"""Unit tests: polygon ingestion, license gate, anonymization rules."""


import pytest

from haze_pipelines.fixtures import fixture_polygon_features
from haze_pipelines.ingest_polygons import (
    anonymized_id,
    fetch_bnpb_features,
    normalize_polygons,
)


def _normalize(features):
    return normalize_polygons(
        features,
        source_dataset="FIXTURE_SOURCE",
        boundary_type="concession",
        license="test-only",
        vintage="2026",
        treatment="synthetic-fixture",
    )


def test_normalize_polygons_marks_attribution_unverified():
    df, report = _normalize(fixture_polygon_features())
    assert report.passed
    assert df["attribution_confidence"].eq("unverified").all()
    assert df["polygon_id"].is_unique
    assert df["boundary_type"].eq("concession").all()


def test_polygon_ids_are_anonymized_not_source_names():
    df, _ = _normalize(fixture_polygon_features())
    for pid in df["polygon_id"]:
        assert pid.startswith("poly_")
        assert "fixture" not in pid.lower()
    assert anonymized_id("FIXTURE_SOURCE", "fixture-a") == df.iloc[0]["polygon_id"]


def test_invalid_geometry_is_skipped_or_repaired():
    features = fixture_polygon_features() + [
        {"type": "Feature", "properties": {"gfwid": "bad"}, "geometry": {"type": "Polygon", "coordinates": []}}
    ]
    df, report = _normalize(features)
    assert len(df) == 2  # broken feature skipped
    assert report.checks[0].name == "non_empty"


def test_fetch_bnpb_requires_license_confirmation():
    with pytest.raises(PermissionError, match="confirm_license"):
        fetch_bnpb_features(confirm_license=False)


def test_fetch_bnpb_paginates_and_deduplicates(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, features):
            self._features = features

        def raise_for_status(self):
            return None

        def json(self):
            return {"type": "FeatureCollection", "features": self._features}

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        offset = params["resultOffset"]
        all_features = fixture_polygon_features()
        if offset == 0:
            page = all_features[:2]
        elif offset == 2:
            # page repeats one feature to prove dedup, and is short to end pagination
            page = [all_features[1]]
        else:
            page = []
        return FakeResponse(page)

    class FakeClient:
        def get(self, url, params=None, timeout=None):
            return fake_get(url, params=params, timeout=timeout)

        def close(self):
            pass

    features = fetch_bnpb_features(client=FakeClient(), page_size=2, confirm_license=True)
    ids = [f["properties"]["gfwid"] for f in features]
    assert sorted(ids) == ["fixture-a", "fixture-b"]
    assert len(calls) == 2
