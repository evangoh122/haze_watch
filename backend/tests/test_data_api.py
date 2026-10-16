"""Tests for the precomputed data endpoints.

Hermetic by design: each test builds a minimal pipeline output in ``tmp_path`` and
points ``settings.data_dir`` at it. The real processed datasets are gitignored, so
CI must never depend on them being generated first.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal, valid pipeline-output tree."""
    processed = tmp_path / "processed"
    processed.mkdir()

    pd.DataFrame(
        [
            {
                "hotspot_id": "h1",
                "latitude": -2.0,
                "longitude": 113.0,
                "observation_time": pd.Timestamp("2026-01-01", tz="UTC"),
                "confidence_pct": 80.0,
                "frp_mw": 5.0,
                "source": "NASA_FIRMS",
                "is_fixture": True,
            }
        ]
    ).to_parquet(processed / "fire_hotspots.parquet", index=False)

    pd.DataFrame(
        [
            {
                "polygon_id": "poly_1",
                "as_of": pd.Timestamp("2026-02-01", tz="UTC"),
                "horizon_hours": 24,
                "hazard_score": 0.5,
                "model_name": "persistence_recency_baseline",
                "model_version": "0.1.0",
                "data_type": "baseline",
                "disclaimer": "Baseline hazard score (0-1), not a calibrated probability.",
            }
        ]
    ).to_parquet(processed / "forecast_baseline.parquet", index=False)

    pd.DataFrame(
        [
            {
                "polygon_id": "poly_1",
                "hotspot_count_in_polygon_30d": 1,
                "hotspot_count_near_30d": 1,
                "area_ha": 1000.0,
            }
        ]
    ).to_parquet(processed / "exposure.parquet", index=False)

    (processed / "exposure_public.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "polygon_id": "poly_1",
                            "caveat": "not confirmed burned area",
                        },
                        "geometry": {"type": "Point", "coordinates": [113.0, -2.0]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


def test_data_endpoints_serve_pipeline_outputs(client: TestClient, data_dir: Path) -> None:
    response = client.get("/api/v1/fires/hotspots?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["treatment"] in ("real", "synthetic-fixture")
    assert "not confirmed burned area" in body["caveat"]
    assert len(body["features"]) <= 5


def test_forecasts_are_labeled_baseline(client: TestClient, data_dir: Path) -> None:
    response = client.get("/api/v1/forecasts?horizon_hours=24&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["data_type"] == "baseline"
    assert "not a calibrated probability" in body["disclaimer"]
    assert len(body["rows"]) <= 5
    for row in body["rows"]:
        assert 0.0 <= row["hazard_score"] <= 1.0


def test_public_exposure_contains_no_attribution_fields(
    client: TestClient, data_dir: Path
) -> None:
    response = client.get("/api/v1/exposure/public")
    assert response.status_code == 200
    features = response.json()["features"]
    assert features
    for feature in features:
        props = feature["properties"]
        for forbidden in ("company", "company_attribution", "group_comp", "name"):
            assert forbidden not in props


def test_missing_dataset_returns_503(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    response = client.get("/api/v1/fires/hotspots")
    assert response.status_code == 503
    assert "Run the ingestion pipeline first" in response.json()["detail"]
