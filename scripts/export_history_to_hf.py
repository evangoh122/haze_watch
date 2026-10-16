"""Export pipeline history to a Hugging Face dataset (repeatable, auditable).

Uploads processed pipeline outputs and the provenance ledger to a private HF
dataset so that historical runs survive local machine loss, scheduled FIRMS
pulls accumulate somewhere durable, and the analyst chat layer can reference
registered history (see scripts/fetch_history_from_hf.py).

LAYOUT: each run uploads to ``runs/<run_id>/`` with the same shape as the local
``data/`` directory (``processed/``, ``metadata/``, ``MANIFEST.json``). Runs
accumulate - the dataset is a history store, not a latest-only mirror - and
``scripts/fetch_history_from_hf.py`` unpacks a chosen run so that
``LLM_DATA_DIR`` grounding works unchanged.

GOVERNANCE (docs/data-sources-and-licensing.md, docs/governance.md):

- Export is an ALLOWLIST: only files explicitly listed here may leave the
  machine. A future dataset is excluded until a human adds it.
- ``plantation_polygons.parquet`` (real-restricted concession geometry) is never
  uploaded - its licence requires verification before redistribution.
- ``exposure.parquet`` is exported only in REDUCED form: centroids rounded to
  0.1 degrees (~11 km), nearest-distance to whole km, and area bucketed to
  500 ha, because exact coordinates/areas/distances are re-identifiable against
  public concession layers. Detection density is dropped entirely (it would
  recover the exact area).
- ``exposure_public.geojson`` (anonymized, simplified) is the only polygon
  geometry that may leave the machine.

Usage:
    uv run python scripts/export_history_to_hf.py              # dry run
    uv run python scripts/export_history_to_hf.py --upload     # private dataset
    uv run python scripts/export_history_to_hf.py --upload --public   # opt-in
    uv run python scripts/export_history_to_hf.py --upload --run-id 2026-02-01-demo
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "data" / "processed"
METADATA = REPO_ROOT / "data" / "metadata"
SAFE_EXPORT_ROOT = REPO_ROOT / "data"  # refuse to write outside this

# The only processed files allowed to leave the machine. Anything else - today
# or added later - is excluded until a human updates this list.
EXPORT_ALLOWLIST = {
    "fire_hotspots.parquet",
    "weather.parquet",
    "environmental_features.parquet",
    "exposure.parquet",  # exported in reduced form only (see reduce_exposure)
    "exposure.summary.json",
    "exposure_public.geojson",
    "forecast_baseline.parquet",
}
METADATA_ALLOWLIST = {"registry.json", "datasets.yaml"}

# Root-level files of the pre-runs/ flat layout, purged explicitly on upload
# (see purge_legacy_flat). Root-only by construction: these bare filenames are
# checked against the remote listing, never matched as patterns, so files under
# runs/<id>/ are untouchable.
LEGACY_FLAT_CLEANUP = sorted(EXPORT_ALLOWLIST | METADATA_ALLOWLIST | {"MANIFEST.json"})

# Reduced exposure: drop precision that would allow re-identification against
# public concession layers (docs/governance.md: "avoid re-identification through
# exact concession coordinates").
#
# Second-pass review hardening:
# - detection_density_per_1000ha is DROPPED: count / density * 1000 recovers the
#   exact area on every row with detections (algebraically defeats bucketing).
# - nearest_hotspot_km_30d is rounded to whole km: an exact distance to a public
#   hotspot places the hidden centroid on a thin circle - tighter than 11 km.
EXPOSURE_KEEP_COLS = [
    "polygon_id",
    "boundary_type",
    "hotspot_count_in_polygon_30d",
    "hotspot_count_near_30d",
    "caveat",
]
CENTROID_DP = 1      # ~11 km
NEAREST_KM_DP = 0    # whole km
AREA_BUCKET_HA = 500
AREA_BUCKET_MIN_HA = 500  # sub-250 ha polygons round up; "0 ha" reads as data loss


def reduce_exposure(src: Path, dest: Path) -> None:
    """Write a distribution-safe exposure table (rounded, bucketed, no exact coords)."""
    df = pd.read_parquet(src)
    out = df[EXPOSURE_KEEP_COLS].copy()
    out["centroid_lon_r"] = df["centroid_lon"].round(CENTROID_DP)
    out["centroid_lat_r"] = df["centroid_lat"].round(CENTROID_DP)
    out["nearest_hotspot_km_r"] = df["nearest_hotspot_km_30d"].round(NEAREST_KM_DP)
    bucketed = (df["area_ha"] / AREA_BUCKET_HA).round(0) * AREA_BUCKET_HA
    out["area_ha_bucket"] = bucketed.clip(lower=AREA_BUCKET_MIN_HA).astype(int)
    out.to_parquet(dest, index=False)


def _assert_safe_export_dir(resolved: Path) -> None:
    """Refuse destinations that overlap the source dirs or leave data/.

    ``--export-dir data/processed`` used to pass a naive ``is_relative_to(data)``
    check and rmtree the pipeline outputs before reading them.
    """
    if not resolved.is_relative_to(SAFE_EXPORT_ROOT.resolve()):
        raise SystemExit(f"refusing to build export outside {SAFE_EXPORT_ROOT}: {resolved}")
    for protected in (PROCESSED.resolve(), METADATA.resolve()):
        if (
            resolved == protected
            or protected.is_relative_to(resolved)
            or resolved.is_relative_to(protected)
        ):
            raise SystemExit(
                f"refusing: export dir {resolved} overlaps source dir {protected} - "
                "building there would delete pipeline outputs"
            )


def build_export(export_dir: Path, run_id: str) -> dict:
    """Build ``export_dir/runs/<run_id>/`` from allowlisted datasets + a manifest.

    Also writes/refreshes ``export_dir/README.md`` (dataset card). Only the run
    directory is rebuilt; previously exported runs under ``export_dir/runs/``
    are left untouched.
    """
    resolved = export_dir.resolve()
    _assert_safe_export_dir(resolved)

    run_dir = export_dir / "runs" / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    processed_out = run_dir / "processed"
    metadata_out = run_dir / "metadata"
    processed_out.mkdir(parents=True)
    metadata_out.mkdir(parents=True)

    included, reduced, excluded = [], [], []
    for src in sorted(PROCESSED.glob("*")):
        if src.name.startswith("."):
            continue
        if src.name not in EXPORT_ALLOWLIST:
            excluded.append(src.name)
            continue
        if src.name == "exposure.parquet":
            reduce_exposure(src, processed_out / src.name)
            included.append(f"processed/{src.name}")
            reduced.append(src.name)
            continue
        shutil.copy2(src, processed_out / src.name)
        included.append(f"processed/{src.name}")

    for src in sorted(METADATA.glob("*")):
        if src.name in METADATA_ALLOWLIST:
            shutil.copy2(src, metadata_out / src.name)
            included.append(f"metadata/{src.name}")

    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": "scripts/export_history_to_hf.py",
        "included": included,
        "reduced_for_distribution": reduced,
        "excluded_not_allowlisted": excluded,
        "treatments": {
            "fire_hotspots.parquet": "synthetic-fixture (fixtures) or real (FIRMS API pulls)",
            "weather.parquet": "real (Open-Meteo / ERA5, attribution required)",
            "environmental_features.parquet": "derived - inherits input treatments",
            "exposure.parquet": "derived - REDUCED: centroids rounded to 0.1 deg, nearest-distance to whole km, area bucketed to 500 ha (min 500); detection density omitted (would recover exact area)",
            "exposure_public.geojson": "real-aggregated (anonymized, simplified)",
            "forecast_baseline.parquet": "baseline hazard score - not a validated forecast",
            "registry.json": "provenance ledger",
        },
        "geometry_note": (
            "No exact concession geometry leaves this machine. plantation_polygons"
            ".parquet (real-restricted) is not distributed. exposure.parquet ships "
            "reduced: location fields rounded to ~11 km and nearest-distance to "
            "whole km, areas bucketed to 500 ha - approximate by design. "
            "exposure_public.geojson is the anonymized public layer."
        ),
    }
    (run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme = f"""---
library_name: pandas
tags:
  - climate-risk
  - geospatial
  - research-prototype
license: other
size_categories:
  - n<1K
---

# Haze Watch - pipeline history

Historical outputs of the Haze Watch geospatial climate-risk pipeline
(research prototype). Each pipeline run is exported to `runs/<run_id>/` with the
same layout as the local `data/` directory (`processed/`, `metadata/`,
`MANIFEST.json`), so runs accumulate instead of overwriting each other. Latest
run: `{run_id}` (generated {manifest["generated_at"]}).

## Per-run files

| File | Treatment |
|---|---|
| `runs/<run_id>/processed/fire_hotspots.parquet` | hotspot detections - synthetic fixtures or real FIRMS pulls (see `registry.json`) |
| `runs/<run_id>/processed/weather.parquet` | real weather observations (Open-Meteo / ERA5 reanalysis) |
| `runs/<run_id>/processed/environmental_features.parquet` | derived point-in-time features |
| `runs/<run_id>/processed/exposure.parquet` | derived exposure counts - **reduced**: centroids rounded to 0.1 deg (~11 km), nearest-distance to whole km, area bucketed to 500 ha |
| `runs/<run_id>/processed/exposure_public.geojson` | anonymized, simplified concession exposure (public-safe layer) |
| `runs/<run_id>/processed/forecast_baseline.parquet` | deterministic baseline hazard scores - NOT calibrated probabilities, NOT PDs |
| `runs/<run_id>/metadata/registry.json` / `datasets.yaml` | provenance ledger: source, licence, treatment, checksums |
| `runs/<run_id>/MANIFEST.json` | per-run manifest incl. reductions and exclusions |

## Deliberately excluded

`plantation_polygons.parquet` - real concession geometry (licence: verify before
redistribution). No exact concession coordinates are distributed in any form:
`exposure.parquet` ships with rounded/bucketed location fields only, and
`exposure_public.geojson` is the anonymized layer.

## Caveats

Research prototype. Companies/financial data referenced downstream are entirely
synthetic. Hotspot counts are detections, not burned area or causation. Hazard
scores are illustrative baselines - not validated forecasts and not
probabilities of default.
"""
    (export_dir / "README.md").write_text(readme, encoding="utf-8")
    return manifest


def purge_legacy_flat(api, dataset: str) -> None:
    """Delete root-level files of the pre-runs/ flat layout (one-off migration).

    Explicit ``CommitOperationDelete`` ops against the remote listing:
    ``upload_folder(delete_patterns=...)`` proved unreliable in the installed
    ``huggingface_hub`` (patterns matched nothing), and ``runs/`` is append-only
    history that must never be mirror-deleted.
    """
    from huggingface_hub import CommitOperationDelete

    remote = set(api.list_repo_files(repo_id=dataset, repo_type="dataset"))
    ops = [
        CommitOperationDelete(path_in_repo=name)
        for name in LEGACY_FLAT_CLEANUP
        if name in remote
    ]
    if ops:
        api.create_commit(
            repo_id=dataset,
            repo_type="dataset",
            operations=ops,
            commit_message="remove legacy flat-layout export (superseded by runs/)",
        )
        print(f"removed {len(ops)} legacy root file(s): {[op.path_in_repo for op in ops]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="egoh33/haze-watch-historical")
    parser.add_argument("--export-dir", default=str(REPO_ROOT / "data" / "hf_export"))
    parser.add_argument(
        "--run-id",
        default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        help="run identifier under runs/ (default: UTC timestamp)",
    )
    parser.add_argument("--upload", action="store_true", help="actually upload (default: build only)")
    parser.add_argument(
        "--public",
        action="store_true",
        help="make the dataset public (default: private - opt-in only)",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    manifest = build_export(export_dir, args.run_id)
    print(f"export built: run {args.run_id}, {len(manifest['included'])} files -> {export_dir}")
    print(f"reduced for distribution: {manifest['reduced_for_distribution']}")
    print(f"excluded (not allowlisted): {manifest['excluded_not_allowlisted']}")

    if not args.upload:
        print("dry run - pass --upload to push to Hugging Face")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    private = not args.public
    api.create_repo(args.dataset, repo_type="dataset", private=private, exist_ok=True)
    # create_repo(exist_ok=True) never changes an existing repo's visibility, so
    # enforce the requested visibility explicitly and verify it.
    api.update_repo_settings(args.dataset, repo_type="dataset", private=private)
    info = api.repo_info(args.dataset, repo_type="dataset")
    if bool(info.private) != private:
        raise SystemExit(
            f"visibility mismatch: requested private={private} but the dataset is "
            f"private={bool(info.private)} - fix it in the HF UI before trusting exports"
        )
    api.upload_folder(
        repo_id=args.dataset,
        repo_type="dataset",
        folder_path=str(export_dir),
        commit_message=f"haze-watch pipeline history run {args.run_id}",
    )
    # Runs accumulate under runs/<id>/ (append-only history). The one-off
    # cleanup of the pre-runs/ flat root layout is explicit, not pattern-based.
    purge_legacy_flat(api, args.dataset)
    print(f"uploaded to https://huggingface.co/datasets/{args.dataset} (private={private})")
    print(f"run path: runs/{args.run_id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
