"""Unit tests: aerosol/haze ingest (CAMS via Open-Meteo Air Quality API)."""

import pandas as pd
import pytest

from haze_pipelines.config import Settings
from haze_pipelines.ingest_aerosol import (
    CANONICAL_COLUMNS,
    default_points,
    ingest_grid,
    normalize_payload,
)
from haze_pipelines.provenance import read_registry

AIR_QUALITY_JSON = {
    "latitude": -2.2,
    "longitude": 113.9,
    "hourly": {
        "time": ["2023-01-01T00:00", "2023-01-01T12:00", "2023-01-02T00:00"],
        "aerosol_optical_depth": [0.2, 0.4, 0.6],
        "pm2_5": [10.0, 20.0, 30.0],
        "pm10": [20.0, 30.0, 40.0],
    },
}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Minimal httpx.Client stand-in: records requests, returns canned JSON."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.requests: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        self.requests.append((url, kwargs))
        # The real API echoes the requested point; mirror that so two grid
        # points produce two distinct grid_ids.
        params = kwargs.get("params") or {}
        payload = dict(self._payload)
        payload["latitude"] = params.get("latitude", payload.get("latitude"))
        payload["longitude"] = params.get("longitude", payload.get("longitude"))
        return _FakeResponse(payload)

    def close(self) -> None:
        return None


def test_normalize_aggregates_hourly_to_daily():
    df = normalize_payload(AIR_QUALITY_JSON)

    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 2  # 3 hourly rows -> 2 day rows
    day1 = df[df["date"] == "2023-01-01"].iloc[0]
    assert day1["aerosol_optical_depth_mean"] == pytest.approx(0.3)
    assert day1["aerosol_optical_depth_max"] == pytest.approx(0.4)
    assert day1["pm2_5_mean"] == pytest.approx(15.0)
    assert day1["grid_id"] == "CAMS-113.90_-2.20"
    assert day1["available_time"] == pd.Timestamp("2023-01-04", tz="UTC")
    assert not df["is_fixture"].any()


def test_normalize_empty_payload_returns_columns():
    df = normalize_payload({"hourly": {"time": []}})
    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 0


def test_default_points_grid():
    points = default_points(bbox=(0.0, 0.0, 2.0, 2.0), grid=3)
    assert len(points) == 9
    assert (2.0, 2.0) in points and (0.0, 0.0) in points


def test_ingest_grid_registers_real_with_depth_note(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    out = tmp_path / "processed" / "haze_aerosol.parquet"

    df, written = ingest_grid(
        [(-2.2, 113.9), (-1.0, 112.0)],
        "2023-01-01",
        "2023-01-02",
        out,
        settings_obj=settings_obj,
        client=_FakeClient(AIR_QUALITY_JSON),
        sleep=None,
    )

    assert written == out and out.exists()
    assert len(df) == 4  # 2 points x 2 days
    entry = {e["dataset_id"]: e for e in read_registry(tmp_path / "metadata")}[
        "haze_aerosol::cams_open_meteo"
    ]
    assert entry["treatment"] == "real"
    assert "2022-08-31" in entry["notes"]  # archive depth limit recorded
    assert "not fire detections" in entry["notes"]
