"""Export pipeline history to a Hugging Face dataset (repeatable, auditable).

Uploads processed pipeline outputs and the provenance ledger to a private HF
dataset so that historical runs survive local machine loss, scheduled FIRMS
pulls accumulate somewhere durable, and the analyst chat layer can reference
registered history (see scripts/fetch_history_from_hf.py).

GOVERNANCE (docs/data-sources-and-licensing.md, docs/governance.md):

- Export is an ALLOWLIST: only files explicitly listed here may leave the
  machine. A future dataset is excluded until a human adds it.
- ``plantation_polygons.parquet`` (real-restricted concession geometry) is never
  uploaded - its licence requires verification before redistribution.
- ``exposure.parquet`` is exported only in REDUCED form: centroids rounded to
  0.1 degrees (~11 km) and area bucketed to 500 ha, because an exact centroid +
  area is re-identifiable against public concession layers.
- ``exposure_public.geojson`` (anonymized, simplified) is the only polygon
  geometry that may leave the machine.

Usage:
    uv run python scripts/export_history_to_hf.py              # dry run
    uv run python scripts/export_history_to_hf.py --upload     # private dataset
    uv run python scripts/export_history_to_hf.py --upload --public   # opt-in
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
SAFE_EXPORT_ROOT = REPO_ROOT / "data"  # refuse to rmtree outside this

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


def build_export(export_dir: Path) -> dict:
    """Copy allowlisted datasets into export_dir and write a manifest + README."""
    resolved = export_dir.resolve()
    if not resolved.is_relative_to(SAFE_EXPORT_ROOT.resolve()):
        raise SystemExit(f"refusing to build export outside {SAFE_EXPORT_ROOT}: {export_dir}")
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)

    included, reduced, excluded = [], [], []
    for src in sorted(PROCESSED.glob("*")):
        if src.name.startswith("."):
            continue
        if src.name not in EXPORT_ALLOWLIST:
            excluded.append(src.name)
            continue
        if src.name == "exposure.parquet":
            reduce_exposure(src, export_dir / src.name)
            included.append(src.name)
            reduced.append(src.name)
            continue
        shutil.copy2(src, export_dir / src.name)
        included.append(src.name)

    for src in sorted(METADATA.glob("*")):
        if src.name in METADATA_ALLOWLIST:
            shutil.copy2(src, export_dir / src.name)
            included.append(src.name)

    manifest = {
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
    (export_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

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
(research prototype). Generated {manifest["generated_at"]}.

## What is here

| File | Treatment |
|---|---|
| `fire_hotspots.parquet` | hotspot detections - synthetic fixtures or real FIRMS pulls (see `registry.json`) |
| `weather.parquet` | real weather observations (Open-Meteo / ERA5 reanalysis) |
| `environmental_features.parquet` | derived point-in-time features |
| `exposure.parquet` | derived exposure counts - **reduced**: centroids rounded to 0.1 deg, area bucketed to 500 ha |
| `exposure_public.geojson` | anonymized, simplified concession exposure (public-safe layer) |
| `forecast_baseline.parquet` | deterministic baseline hazard scores - NOT calibrated probabilities, NOT PDs |
| `registry.json` / `datasets.yaml` | provenance ledger: source, licence, treatment, checksums |
| `MANIFEST.json` | export manifest incl. reductions and exclusions |

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="egoh33/haze-watch-historical")
    parser.add_argument("--export-dir", default=str(REPO_ROOT / "data" / "hf_export"))
    parser.add_argument("--upload", action="store_true", help="actually upload (default: build only)")
    parser.add_argument(
        "--public",
        action="store_true",
        help="make the dataset public (default: private - opt-in only)",
    )
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    manifest = build_export(export_dir)
    print(f"export built: {len(manifest['included'])} files -> {export_dir}")
    print(f"reduced for distribution: {manifest['reduced_for_distribution']}")
    print(f"excluded (not allowlisted): {manifest['excluded_not_allowlisted']}")

    if not args.upload:
        print("dry run - pass --upload to push to Hugging Face")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    private = not args.public
    api.create_repo(args.dataset, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        repo_id=args.dataset,
        repo_type="dataset",
        folder_path=str(export_dir),
        commit_message="haze-watch pipeline history export",
        delete_patterns="*",  # remote must mirror the allowlist exactly
    )
    print(f"uploaded to https://huggingface.co/datasets/{args.dataset} (private={private})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
