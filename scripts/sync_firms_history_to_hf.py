"""Sync FIRMS hotspot history into the HF dataset as GeoParquet.

Pulls detections via the FIRMS area API (chunked <=5-day windows, deduplicated),
writes GeoParquet (WKB Point geometry + GeoParquet ``geo`` metadata), merges
with the per-year files already in the dataset and uploads to
``history/fire_hotspots/sensor=SENSOR/year=YYYY.parquet`` in
``egoh33/haze-watch-historical`` (per-sensor files so concurrent sensor
backfills never overwrite each other).

The data is NASA FIRMS detections (public, attribution required) - the same
class of data already distributed under ``runs/*/processed/fire_hotspots``.
No restricted concession geometry passes through this script.

Run locally (FIRMS_API_KEY + HF auth) or from CI
(``.github/workflows/firms-ingest.yml`` - secrets FIRMS_API_KEY + HF_TOKEN):

    uv run python scripts/sync_firms_history_to_hf.py --backfill-days 7
    uv run python scripts/sync_firms_history_to_hf.py --start-date 2000-11-01 --backfill-days 9500 --sensor MODIS_NRT
    uv run python scripts/sync_firms_history_to_hf.py --dry-run   # fetch + write, no upload
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = "egoh33/haze-watch-historical"
HISTORY_PREFIX = "history/fire_hotspots"


def history_path(sensor: str, year: int) -> str:
    # Per-sensor files so concurrent sensor backfills never overwrite each other.
    return f"{HISTORY_PREFIX}/sensor={sensor}/year={year}.parquet"


def load_remote_year(dataset: str, sensor: str, year: int) -> pd.DataFrame | None:
    """Download a stored year (without its geometry column) or None if absent."""
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError

    try:
        local = hf_hub_download(
            repo_id=dataset, repo_type="dataset", filename=history_path(sensor, year)
        )
    except EntryNotFoundError:
        return None
    return pd.read_parquet(local).drop(columns=["geometry"], errors="ignore")


def sync_history(
    *,
    dataset: str,
    start_date: str | None,
    backfill_days: int,
    sensor: str,
    area: str,
    out_dir: Path,
    dry_run: bool = False,
    progress=None,
) -> dict[int, tuple[int, int]]:
    """Fetch a range and sync it into per-year GeoParquet files.

    Returns ``{year: (fetched_rows, merged_rows)}``.
    """
    from haze_pipelines.geoparquet import merge_hotspots, points_to_geoparquet
    from haze_pipelines.ingest_firms import fetch_firms_range

    frames: list[pd.DataFrame] = []
    if start_date is None:
        # Trailing window: DATE-anchored at today-backfill_days+1.
        from datetime import date as date_cls
        from datetime import timedelta

        start_date = (date_cls.today() - timedelta(days=backfill_days - 1)).isoformat()
    frames.append(
        fetch_firms_range(
            area,
            start_date,
            backfill_days,
            sensor=sensor,
            progress=progress,
        )
    )
    df = pd.concat(frames, ignore_index=True)
    if not len(df):
        return {}

    from huggingface_hub import HfApi

    api = HfApi()
    results: dict[int, tuple[int, int]] = {}
    for year_value, chunk in df.groupby(df["observation_time"].dt.year):
        year = int(year_value)
        # Local files mirror the per-sensor remote layout so concurrent sensor
        # runs never overwrite each other's year files before upload.
        existing = load_remote_year(dataset, sensor, year)
        merged = merge_hotspots(existing, chunk)
        out = out_dir / f"sensor={sensor}" / f"year={year}.parquet"
        points_to_geoparquet(merged, out)
        results[year] = (len(chunk), len(merged))
        if not dry_run:
            api.upload_file(
                path_or_fileobj=str(out),
                path_in_repo=history_path(sensor, year),
                repo_id=dataset,
                repo_type="dataset",
                commit_message=f"firms history {year}: +{len(chunk)} rows -> {len(merged)} total",
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--sensor", default="MODIS_NRT")
    parser.add_argument("--area", default=None, help="west,south,east,north (default: Indonesia)")
    parser.add_argument("--start-date", default="", help="YYYY-MM-DD (default: trailing window)")
    parser.add_argument("--backfill-days", type=int, default=7)
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "data" / "history_geo"))
    parser.add_argument("--dry-run", action="store_true", help="fetch + write locally, no upload")
    args = parser.parse_args()

    from haze_pipelines.ingest_firms import default_area

    results = sync_history(
        dataset=args.dataset,
        start_date=args.start_date or None,
        backfill_days=args.backfill_days,
        sensor=args.sensor,
        area=args.area or default_area(),
        out_dir=Path(args.out_dir),
        dry_run=args.dry_run,
        progress=lambda msg: print(f"  {msg}"),
    )
    if not results:
        print("no detections fetched - nothing to sync")
        return 0
    for year, (fetched, total) in sorted(results.items()):
        suffix = " (dry run)" if args.dry_run else ""
        print(f"  {year}: fetched {fetched} rows -> {total} rows in history{suffix}")
    print(f"synced {len(results)} year file(s) to {args.dataset} ({HISTORY_PREFIX}/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
