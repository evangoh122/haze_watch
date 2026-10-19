"""Unit tests: NASA POWER / MERRA-2 weather fallback normalization."""

import pandas as pd

from haze_pipelines.config import Settings
from haze_pipelines.ingest_power import ingest_stations, normalize_power_payload
from haze_pipelines.ingest_weather import CANONICAL_COLUMNS
from haze_pipelines.provenance import read_registry

POWER_JSON = {
    "geometry": {"coordinates": [116.32, -0.08, 0.0]},
    "properties": {
        "parameter": {
            "T2M_MAX": {"20230101": 31.0, "20230102": 32.0, "20230103": -999.0},
            "PRECTOTCORR": {"20230101": 0.0, "20230102": 5.0, "20230103": -999.0},
            "RH2M": {"20230101": 80.0, "20230102": 75.0, "20230103": -999.0},
            "WS10M": {"20230101": 3.0, "20230102": 4.0, "20230103": -999.0},
        }
    },
}


def test_normalize_power_payload_maps_missing_and_lag():
    df = normalize_power_payload(
        POWER_JSON, "POWER-1", availability_lag_hours=48.0
    )

    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 2  # the all-missing tail day is dropped
    first = df.iloc[0]
    assert first["station_id"] == "POWER-1"
    assert first["temperature_max_c"] == 31.0
    assert first["precipitation_sum_mm"] == 0.0
    assert first["available_time"] == pd.Timestamp("2023-01-03", tz="UTC")


def test_normalize_power_payload_keeps_partial_missing_values():
    payload = {
        "properties": {
            "parameter": {
                "T2M_MAX": {"20230101": 31.0},
                "PRECTOTCORR": {"20230101": -999.0},
                "RH2M": {"20230101": 80.0},
                "WS10M": {"20230101": 3.0},
            }
        }
    }
    df = normalize_power_payload(payload, "POWER-1", latitude=-0.08, longitude=116.32)
    row = df.iloc[0]
    assert row["temperature_max_c"] == 31.0
    assert pd.isna(row["precipitation_sum_mm"])
    assert row["latitude"] == -0.08
    assert row["longitude"] == 116.32


def test_power_ingest_registers_source(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    out = tmp_path / "processed" / "weather.parquet"
    df, written = ingest_stations(
        [{"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}],
        "2023-01-01",
        "2023-01-03",
        out,
        settings_obj=settings_obj,
        client=_FakeClient(POWER_JSON),
        pause_seconds=0,
    )
    assert written == out and len(df) == 2
    entry = {e["dataset_id"]: e for e in read_registry(tmp_path / "metadata")}[
        "weather_observations::nasa_power"
    ]
    assert entry["treatment"] == "real"
    assert "MERRA-2" in entry["name"]
    assert "not ERA5" in entry["notes"]


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(self._payload)

    def close(self) -> None:
        return None
