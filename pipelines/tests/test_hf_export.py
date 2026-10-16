"""Regression tests for scripts/export_history_to_hf.py.

Covers the review findings: dest-overlap data loss, reduced-exposure schema
(re-identification hardening), and the runs/<id>/ layout that grounding and
fetch_history_from_hf.py depend on.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_history_to_hf.py"


def _load_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    spec = importlib.util.spec_from_file_location("export_history_to_hf", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    processed = tmp_path / "data" / "processed"
    metadata = tmp_path / "data" / "metadata"
    processed.mkdir(parents=True)
    metadata.mkdir(parents=True)
    monkeypatch.setattr(mod, "PROCESSED", processed)
    monkeypatch.setattr(mod, "METADATA", metadata)
    monkeypatch.setattr(mod, "SAFE_EXPORT_ROOT", tmp_path / "data")
    return mod, processed, metadata


def _write_inputs(processed: Path, metadata: Path) -> None:
    exposure = pd.DataFrame(
        {
            "polygon_id": ["poly_a", "poly_b"],
            "boundary_type": ["concession", "concession"],
            "hotspot_count_in_polygon_30d": [2, 0],
            "hotspot_count_near_30d": [5, 1],
            "nearest_hotspot_km_30d": [358.217343938937, 28.64970075394316],
            "detection_density_per_1000ha": [0.118, 0.0],
            "centroid_lon": [116.771991, 116.060157],
            "centroid_lat": [1.149088, -1.855789],
            "area_ha": [16894.0, 94.0],
            "caveat": ["fixture", "fixture"],
        }
    )
    exposure.to_parquet(processed / "exposure.parquet", index=False)
    pd.DataFrame({"lat": [1.0], "lon": [116.0]}).to_parquet(
        processed / "fire_hotspots.parquet", index=False
    )
    # Non-allowlisted file must never leave the machine.
    pd.DataFrame({"secret": [1]}).to_parquet(processed / "plantation_polygons.parquet", index=False)
    (metadata / "registry.json").write_text(json.dumps([{"dataset_id": "exposure::test"}]), encoding="utf-8")


def test_export_refuses_dest_overlapping_sources(monkeypatch, tmp_path):
    """--export-dir data/processed (or data/) used to rmtree the pipeline outputs."""
    mod, processed, metadata = _load_module(monkeypatch, tmp_path)
    _write_inputs(processed, metadata)
    for bad in (processed, tmp_path / "data", metadata, processed / "sub"):
        with pytest.raises(SystemExit):
            mod.build_export(bad, "run1")
    assert (processed / "exposure.parquet").exists()  # sources untouched


def test_export_refuses_outside_data(monkeypatch, tmp_path):
    mod, processed, metadata = _load_module(monkeypatch, tmp_path)
    _write_inputs(processed, metadata)
    with pytest.raises(SystemExit):
        mod.build_export(tmp_path / "elsewhere", "run1")


def test_reduced_exposure_has_no_reidentifying_fields(monkeypatch, tmp_path):
    mod, processed, metadata = _load_module(monkeypatch, tmp_path)
    _write_inputs(processed, metadata)
    mod.build_export(tmp_path / "data" / "hf_export", "run1")

    out = pd.read_parquet(tmp_path / "data" / "hf_export" / "runs" / "run1" / "processed" / "exposure.parquet")
    for col in ("centroid_lon", "centroid_lat", "area_ha", "detection_density_per_1000ha", "nearest_hotspot_km_30d"):
        assert col not in out.columns, f"re-identifying column leaked: {col}"
    assert {"centroid_lon_r", "centroid_lat_r", "nearest_hotspot_km_r", "area_ha_bucket"} <= set(out.columns)
    assert out["centroid_lon_r"].iloc[0] == pytest.approx(116.8, abs=0.05)  # 1 dp
    assert out["nearest_hotspot_km_r"].iloc[0] == 358.0  # whole km
    assert (out["area_ha_bucket"] >= 500).all()  # no "0 ha" bucket


def test_export_layout_matches_grounding_shape(monkeypatch, tmp_path):
    """runs/<id>/{processed,metadata,MANIFEST.json} mirrors data/ so LLM_DATA_DIR works."""
    mod, processed, metadata = _load_module(monkeypatch, tmp_path)
    _write_inputs(processed, metadata)
    export_dir = tmp_path / "data" / "hf_export"
    mod.build_export(export_dir, "run1")

    run_dir = export_dir / "runs" / "run1"
    assert (run_dir / "processed" / "exposure.parquet").is_file()
    assert (run_dir / "processed" / "fire_hotspots.parquet").is_file()
    assert (run_dir / "metadata" / "registry.json").is_file()
    assert (run_dir / "MANIFEST.json").is_file()
    assert (export_dir / "README.md").is_file()

    manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run1"
    assert "plantation_polygons.parquet" in manifest["excluded_not_allowlisted"]
    assert not any("plantation" in name for name in manifest["included"])

    # Legacy cleanup is a fixed root-level name list, checked against the remote
    # listing (never pattern-matched), so runs/<id>/ files are untouchable.
    assert all("*" not in p and "/" not in p for p in mod.LEGACY_FLAT_CLEANUP)
