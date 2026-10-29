"""Unit tests: weather normalization from Open-Meteo payloads."""

from datetime import UTC, datetime

import pandas as pd

from haze_pipelines.config import Settings
from haze_pipelines.ingest_power import ingest_stations as ingest_power_stations
from haze_pipelines.ingest_weather import grid_stations, ingest_stations, normalize_station_payload

FAKE_PAYLOAD = {
    "latitude": -2.2144,
    "longitude": 113.9186,
    "daily": {
        "time": ["2026-01-01", "2026-01-02"],
        "temperature_2m_max": [33.1, 34.0],
        "precipitation_sum": [10.0, 0.0],
        "relative_humidity_2m_mean": [70, 68],
        "wind_speed_10m_max": [12.0, 9.5],
    },
}


def test_normalize_station_payload_schema_and_lag():
    df = normalize_station_payload(FAKE_PAYLOAD, "STN-1", availability_lag_hours=48.0)
    assert len(df) == 2
    assert df["station_id"].eq("STN-1").all()
    first = df.iloc[0]
    assert first["observation_time"] == datetime(2026, 1, 1, tzinfo=UTC)
    assert first["available_time"] == datetime(2026, 1, 3, tzinfo=UTC)
    assert first["temperature_max_c"] == 33.1


def test_normalize_station_payload_empty_payload():
    df = normalize_station_payload({"latitude": 0, "longitude": 0, "daily": {}}, "STN-2")
    assert df.empty


def test_grid_stations_covers_bbox_with_stable_ids():
    stations = grid_stations(bbox=(110.0, -4.0, 120.0, 6.0), grid=6)
    assert len(stations) == 36
    ids = [s["station_id"] for s in stations]
    assert len(ids) == len(set(ids))
    assert "ERA5-110E-4S" in ids
    assert "ERA5-120E-6N" in ids
    assert min(s["latitude"] for s in stations) == -4.0
    assert max(s["longitude"] for s in stations) == 120.0


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        params = kwargs.get("params") or {}
        return _FakeResponse(
            {
                "latitude": params["latitude"],
                "longitude": params["longitude"],
                "daily": {
                    "time": ["2026-01-01", "2026-01-02"],
                    "temperature_2m_max": [31.0, 32.0],
                    "precipitation_sum": [0.0, 1.0],
                    "relative_humidity_2m_mean": [70.0, 72.0],
                    "wind_speed_10m_max": [5.0, 6.0],
                },
            }
        )

    def close(self) -> None:
        return None


def test_ingest_stations_resumes_from_checkpoints(tmp_path):
    stations = [
        {"station_id": "STN-A", "label": "A", "latitude": -2.0, "longitude": 113.0},
        {"station_id": "STN-B", "label": "B", "latitude": 0.0, "longitude": 116.0},
    ]
    settings_obj = Settings(data_dir=tmp_path)
    checkpoint_dir = tmp_path / "partial"

    first, _ = ingest_stations(
        stations,
        "2026-01-01",
        "2026-01-02",
        tmp_path / "weather.parquet",
        settings_obj=settings_obj,
        client=_FakeClient(),
        checkpoint_dir=checkpoint_dir,
    )
    assert len(first) == 4
    assert sorted(path.name for path in checkpoint_dir.glob("*.parquet")) == [
        "era5-STN-A--2.0000-113.0000-20260101-20260102.parquet",
        "era5-STN-B-0.0000-116.0000-20260101-20260102.parquet",
    ]

    # A rerun must not touch the API: both stations are already checkpointed.
    second, _ = ingest_stations(
        stations,
        "2026-01-01",
        "2026-01-02",
        tmp_path / "weather.parquet",
        settings_obj=settings_obj,
        client=object(),  # any attribute access would fail if a fetch were attempted
        checkpoint_dir=checkpoint_dir,
    )
    assert len(second) == 4


class _ParamWeatherClient:
    """An Open-Meteo client that echoes the requested point and date window."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        params = kwargs.get("params") or {}
        self.calls.append(dict(params))
        days = [
            day.strftime("%Y-%m-%d")
            for day in pd.date_range(params["start_date"], params["end_date"])
        ]
        return _FakeResponse(
            {
                "latitude": params["latitude"],
                "longitude": params["longitude"],
                "daily": {
                    "time": days,
                    "temperature_2m_max": [20.0] * len(days),
                    "precipitation_sum": [1.0] * len(days),
                    "relative_humidity_2m_mean": [70.0] * len(days),
                    "wind_speed_10m_max": [5.0] * len(days),
                },
            }
        )

    def close(self) -> None:
        return None


def test_weather_checkpoint_is_keyed_by_date_range_and_coordinates(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "STN-A", "label": "A", "latitude": -2.0, "longitude": 113.0}

    ingest_stations(
        [station],
        "2026-01-01",
        "2026-01-02",
        out,
        settings_obj=settings_obj,
        client=_ParamWeatherClient(),
        checkpoint_dir=checkpoint_dir,
    )

    february_client = _ParamWeatherClient()
    february, _ = ingest_stations(
        [station],
        "2026-02-01",
        "2026-02-03",
        out,
        settings_obj=settings_obj,
        client=february_client,
        checkpoint_dir=checkpoint_dir,
    )
    assert february_client.calls, "a new date range must not reuse the January checkpoint"
    assert february["observation_time"].dt.month.unique().tolist() == [2]
    assert len(february) == 3

    moved = {"station_id": "STN-A", "label": "A", "latitude": 1.0, "longitude": 115.0}
    moved_client = _ParamWeatherClient()
    moved_df, _ = ingest_stations(
        [moved],
        "2026-01-01",
        "2026-01-02",
        out,
        settings_obj=settings_obj,
        client=moved_client,
        checkpoint_dir=checkpoint_dir,
    )
    assert moved_client.calls, "a new coordinate pair must not reuse the old checkpoint"
    assert moved_df["latitude"].unique().tolist() == [1.0]
    assert len(list(checkpoint_dir.glob("era5-*.parquet"))) == 3


POWER_PAYLOAD = {
    "properties": {
        "parameter": {
            "T2M_MAX": {"20230101": 31.0, "20230102": 32.0},
            "PRECTOTCORR": {"20230101": 0.0, "20230102": 0.0},
            "RH2M": {"20230101": 80.0, "20230102": 80.0},
            "WS10M_MAX": {"20230101": 5.0, "20230102": 6.0},
        }
    }
}


class _PowerClient:
    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(POWER_PAYLOAD)

    def close(self) -> None:
        return None


def test_power_and_weather_checkpoints_do_not_collide(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    checkpoint_dir = tmp_path / "partial"
    station = {"station_id": "SHARED", "label": "shared", "latitude": -2.0, "longitude": 113.0}

    power_df, _ = ingest_power_stations(
        [{"station_id": "SHARED", "latitude": -2.0, "longitude": 113.0}],
        "2023-01-01",
        "2023-01-02",
        tmp_path / "power.parquet",
        settings_obj=settings_obj,
        client=_PowerClient(),
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
    )
    assert power_df["temperature_max_c"].tolist() == [31.0, 32.0]

    weather_df, _ = ingest_stations(
        [station],
        "2023-01-01",
        "2023-01-02",
        tmp_path / "weather.parquet",
        settings_obj=settings_obj,
        client=_ParamWeatherClient(),
        checkpoint_dir=checkpoint_dir,
    )
    assert weather_df["temperature_max_c"].tolist() == [20.0, 20.0]
    assert len(list(checkpoint_dir.glob("power-*.parquet"))) == 1
    assert len(list(checkpoint_dir.glob("era5-*.parquet"))) == 1
