"""Tests for provenance treatment derivation (governance regression suite).

Regression cover for the labeling bug where fixture-derived outputs were
registered as treatment="real" while run summaries said "synthetic-fixture".
"""


from haze_pipelines.build_features import build_and_save
from haze_pipelines.config import Settings
from haze_pipelines.fixtures import fixture_hotspots, fixture_polygon_features
from haze_pipelines.ingest_firms import normalize_firms
from haze_pipelines.ingest_polygons import normalize_polygons
from haze_pipelines.io import write_parquet
from haze_pipelines.provenance import derive_treatment, read_registry


def test_derive_treatment_flags_synthetic_inputs():
    assert derive_treatment(True) == "synthetic-fixture"
    assert derive_treatment("real", "synthetic-fixture") == "synthetic-fixture"
    assert derive_treatment(False, "real") == "real"


def test_derive_treatment_inherits_restriction():
    """real-restricted inputs keep the restriction on derived outputs."""
    assert derive_treatment(False, "real-restricted") == "real-restricted"
    assert derive_treatment("real-restricted") == "real-restricted"


def test_derive_treatment_never_defaults_to_real_on_unknown_inputs():
    assert derive_treatment(None) == "derived-unverified"
    assert derive_treatment("real", None) == "derived-unverified"
    assert derive_treatment("something-else") == "derived-unverified"
    # No inputs at all is unknown, not real.
    assert derive_treatment() == "derived-unverified"


def test_registry_labels_fixture_derived_features_as_synthetic(tmp_path):
    """End-to-end: fixture hotspots -> features must register as synthetic-fixture."""
    data_dir = tmp_path
    settings_obj = Settings(data_dir=data_dir)

    polygons = normalize_polygons(
        fixture_polygon_features(),
        source_dataset="FIXTURE",
        boundary_type="concession",
        license="test",
        vintage="2026",
        treatment="synthetic-fixture",
    )[0]
    hotspots = normalize_firms(
        fixture_hotspots(n=6), source="FIXTURE", available_lag_hours=1.0, is_fixture=True
    )

    polygons_path = data_dir / "processed" / "polygons.parquet"
    hotspots_path = data_dir / "processed" / "hotspots.parquet"
    write_parquet(polygons, polygons_path)
    write_parquet(hotspots, hotspots_path)

    _, out_path = build_and_save(
        polygons_path,
        hotspots_path,
        None,
        "2026-01-02T00:00:00Z",
        data_dir / "processed" / "features.parquet",
        settings_obj=settings_obj,
    )

    registry = {e["dataset_id"]: e for e in read_registry(data_dir / "metadata")}
    entry = next(e for e in registry.values() if e["dataset_id"].startswith("environmental_features"))
    assert entry["treatment"] == "synthetic-fixture"

    # The Parquet metadata must agree with the registry.
    from haze_pipelines.io import read_geo_metadata

    assert read_geo_metadata(out_path)["treatment"] == "synthetic-fixture"
