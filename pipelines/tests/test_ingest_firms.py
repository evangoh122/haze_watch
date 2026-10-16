"""Unit tests: FIRMS hotspot normalization and validation."""

import pandas as pd
import pytest

from haze_pipelines.config import Settings
from haze_pipelines.fixtures import fixture_hotspots
from haze_pipelines.ingest_firms import (
    default_area,
    fetch_firms_area,
    fetch_firms_range,
    ingest_from_api,
    normalize_firms,
)
from haze_pipelines.provenance import read_registry
from haze_pipelines.quality import validate_hotspots


def test_normalize_firms_canonical_schema():
    raw = fixture_hotspots(n=5)
    out = normalize_firms(raw, source="FIXTURE", available_lag_hours=3.0, is_fixture=True)

    assert len(out) == 5
    assert out["source"].eq("FIXTURE").all()
    assert out["is_fixture"].all()
    assert out["hotspot_id"].is_unique
    # availability never precedes observation
    assert (out["available_time"] >= out["observation_time"]).all()


def test_normalize_firms_deduplicates_identical_detections():
    raw = fixture_hotspots(n=4)
    doubled = pd.concat([raw, raw], ignore_index=True)
    out = normalize_firms(doubled, source="FIXTURE", available_lag_hours=3.0, is_fixture=True)
    assert len(out) == 4


def test_normalize_firms_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        normalize_firms(pd.DataFrame({"latitude": [1.0]}), source="X", available_lag_hours=1.0)


def test_normalize_real_firms_schema_acq_date_acq_time_hhmm_int():
    """Regression: actual FIRMS exports use acq_date/acq_time (HHMM integer).

    The fixture previously used non-standard acquired_* names, so tests passed
    while real downloads would have been rejected.
    """
    real_export = pd.DataFrame(
        {
            "latitude": [-2.21, -1.10],
            "longitude": [113.92, 112.30],
            "brightness": [321.5, 330.1],
            "scan": [1.0, 1.1],
            "track": [1.0, 1.0],
            "acq_date": ["2026-09-15", "2026-09-15"],
            "acq_time": [430, 1830],  # HHMM integers, as FIRMS writes them
            "satellite": ["Terra", "Aqua"],
            "confidence": [65, 80],
            "version": ["6.1NRT", "6.1NRT"],
            "bright_t31": [296.0, 297.5],
            "frp": [5.2, 12.9],
            "daynight": ["D", "N"],
            "type": [0, 0],
        }
    )
    out = normalize_firms(real_export, source="NASA_FIRMS", available_lag_hours=3.0)

    assert len(out) == 2
    assert out["observation_time"].dt.strftime("%H:%M").tolist() == ["04:30", "18:30"]
    assert out["confidence_pct"].tolist() == [65.0, 80.0]
    assert (out["available_time"] > out["observation_time"]).all()


def test_normalize_real_firms_viirs_brightness_column():
    """VIIRS exports carry bright_ti4 instead of brightness."""
    viirs = pd.DataFrame(
        {
            "latitude": [-2.21],
            "longitude": [113.92],
            "bright_ti4": [325.4],
            "acq_date": ["2026-09-15"],
            "acq_time": [815],
            "satellite": ["NPP"],
            "confidence": ["high"],
            "frp": [3.3],
            "daynight": ["D"],
        }
    )
    out = normalize_firms(viirs, source="NASA_FIRMS_VIIRS", available_lag_hours=3.0)
    assert out["brightness_k"].iloc[0] == 325.4
    assert out["confidence_pct"].iloc[0] == 90.0  # "high" label mapped
    assert out["observation_time"].dt.strftime("%H:%M").iloc[0] == "08:15"


def test_hotspot_quality_passes_on_normalized_fixture():
    raw = fixture_hotspots(n=6)
    out = normalize_firms(raw, source="FIXTURE", available_lag_hours=3.0, is_fixture=True)
    report = validate_hotspots(out)
    assert report.passed, [c.name for c in report.errors]


# --- automatic pulls (FIRMS area API) ---------------------------------------

# A minimal FIRMS-shaped CSV (as the area API returns it), key-free in tests.
FIRMS_CSV = (
    "latitude,longitude,bright_ti4,acq_date,acq_time,satellite,confidence,frp,daynight\n"
    "-2.21,113.92,325.4,2026-09-15,430,NPP,high,5.2,D\n"
    "-1.10,112.30,330.1,2026-09-15,1830,N20,80,12.9,N\n"
)


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeClient:
    """Minimal httpx.Client stand-in: records URLs, returns canned CSV."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.urls: list[str] = []

    def get(self, url: str, **_: object) -> _FakeResponse:
        self.urls.append(url)
        return _FakeResponse(self._text)

    def close(self) -> None:
        return None


def test_default_area_is_the_indonesia_bbox():
    assert default_area() == "94.0,-11.5,141.5,6.5"


def test_fetch_firms_area_builds_url_and_normalizes():
    client = _FakeClient(FIRMS_CSV)
    df = fetch_firms_area(
        "94,-11.5,141.5,6.5", 3, api_key="KEY", client=client, sensor="VIIRS_SNPP_NRT"
    )

    assert len(df) == 2
    assert df["source"].eq("NASA_FIRMS_VIIRS_SNPP_NRT").all()
    assert not df["is_fixture"].any()
    assert client.urls[0].endswith("/3")
    assert "VIIRS_SNPP_NRT" in client.urls[0] and "KEY" in client.urls[0]
    # HHMM integers from the real API must normalize to HH:MM
    assert df["observation_time"].dt.strftime("%H:%M").tolist() == ["04:30", "18:30"]


def test_fetch_firms_area_requires_key():
    with pytest.raises(RuntimeError, match="FIRMS API key not configured"):
        fetch_firms_area("94,-11.5,141.5,6.5", 1, api_key="", client=_FakeClient(FIRMS_CSV))


def test_fetch_firms_area_rejects_out_of_range_days():
    with pytest.raises(ValueError, match="1-5 days"):
        fetch_firms_area("94,-11.5,141.5,6.5", 6, api_key="KEY", client=_FakeClient(FIRMS_CSV))
    with pytest.raises(ValueError, match="1-5 days"):
        fetch_firms_area("94,-11.5,141.5,6.5", 0, api_key="KEY", client=_FakeClient(FIRMS_CSV))


def test_ingest_from_api_writes_and_registers_as_real(tmp_path):
    settings_obj = Settings(data_dir=tmp_path, firms_api_key="KEY")
    out = tmp_path / "processed" / "fire_hotspots.parquet"

    df, written = ingest_from_api(
        out, sensor="MODIS_NRT", settings_obj=settings_obj, client=_FakeClient(FIRMS_CSV)
    )

    assert written == out and out.exists()
    assert len(df) == 2
    entry = {e["dataset_id"]: e for e in read_registry(tmp_path / "metadata")}[
        "fire_hotspots::nasa_firms"
    ]
    assert entry["treatment"] == "real"
    assert "area=" in entry["source"]
    assert "KEY" not in entry["source"]  # the API key must never be recorded


def test_fetch_firms_area_appends_date_param():
    client = _FakeClient(FIRMS_CSV)
    fetch_firms_area(
        "94,-11.5,141.5,6.5", 3, api_key="KEY", client=client, date="2015-09-01"
    )
    assert client.urls[0].endswith("/3/2015-09-01")


def test_fetch_firms_area_rejects_malformed_date():
    with pytest.raises(ValueError):
        fetch_firms_area(
            "94,-11.5,141.5,6.5", 3, api_key="KEY", client=_FakeClient(FIRMS_CSV), date="01-09-2015"
        )


def test_fetch_firms_range_chunks_windows_and_dedups():
    """12 days -> 3 requests (5+5+2); identical rows across windows dedup on hotspot_id."""
    client = _FakeClient(FIRMS_CSV)
    sleeps: list[float] = []
    df = fetch_firms_range(
        "94,-11.5,141.5,6.5",
        "2015-09-01",
        12,
        api_key="KEY",
        client=client,
        sleep=sleeps.append,
    )

    assert [u.rsplit("/", 2)[-2:] for u in client.urls] == [
        ["5", "2015-09-01"],
        ["5", "2015-09-06"],
        ["2", "2015-09-11"],
    ]
    assert len(sleeps) == 2  # paced between windows only
    assert len(df) == 2  # same 2 rows returned every window -> deduplicated


def test_ingest_from_api_backfill_registers_range(tmp_path):
    settings_obj = Settings(data_dir=tmp_path, firms_api_key="KEY")
    out = tmp_path / "processed" / "fire_hotspots.parquet"

    df, written = ingest_from_api(
        out,
        sensor="MODIS_NRT",
        start_date="2015-09-01",
        backfill_days=12,
        settings_obj=settings_obj,
        client=_FakeClient(FIRMS_CSV),
    )

    assert written == out and len(df) == 2
    entry = {e["dataset_id"]: e for e in read_registry(tmp_path / "metadata")}[
        "fire_hotspots::nasa_firms"
    ]
    assert "start=2015-09-01" in entry["source"]
    assert "backfill_days=12" in entry["source"]
    assert "NRT" in entry["notes"]  # SP/NRT distinction recorded
    assert "KEY" not in entry["source"]
