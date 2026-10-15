"""Tests for the precomputed data endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_data_endpoints_serve_pipeline_outputs():
    """The repo's processed datasets should be readable through the API."""
    response = client.get("/api/v1/fires/hotspots?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["treatment"] in ("real", "synthetic-fixture")
    assert "not confirmed burned area" in body["caveat"]
    assert len(body["features"]) <= 5


def test_forecasts_are_labeled_baseline():
    response = client.get("/api/v1/forecasts?horizon_hours=24&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["data_type"] == "baseline"
    assert "not a calibrated probability" in body["disclaimer"]
    assert len(body["rows"]) <= 5
    for row in body["rows"]:
        assert 0.0 <= row["hazard_score"] <= 1.0


def test_public_exposure_contains_no_attribution_fields():
    response = client.get("/api/v1/exposure/public")
    assert response.status_code == 200
    features = response.json()["features"]
    assert features
    for feature in features:
        props = feature["properties"]
        for forbidden in ("company", "company_attribution", "group_comp", "name"):
            assert forbidden not in props


def test_missing_dataset_returns_503(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    response = client.get("/api/v1/fires/hotspots")
    assert response.status_code == 503
    assert "Run the ingestion pipeline first" in response.json()["detail"]
