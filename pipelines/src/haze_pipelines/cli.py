"""Command-line interface: ``haze-pipelines``.

Designed for scheduled batch execution (cron / GitHub Actions) and local runs:

    haze-pipelines ingest-firms --input data/raw/firms --out data/processed/fire_hotspots.parquet
    haze-pipelines ingest-weather --stations data/raw/stations.csv --start 2026-01-01 --end 2026-01-31
    haze-pipelines ingest-polygons --input data/raw/concessions/bnpb.geojson \
        --source BNPB_GlobalForestWatch2 --boundary-type concession \
        --license "GFW custom licence - verify before redistribution" --vintage 2025 \
        --out data/processed/plantation_polygons.parquet
    haze-pipelines build-features --as-of 2026-02-01
    haze-pipelines run-exposure --as-of 2026-02-01
    haze-pipelines run-forecast --features data/processed/environmental_features.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from .config import Settings
from .io import read_parquet


def _cmd_ingest_firms(args: argparse.Namespace) -> int:
    if args.from_api:
        from .ingest_firms import ingest_from_api

        try:
            df, out = ingest_from_api(
                Path(args.out),
                area=args.area,
                days=args.days,
                sensor=args.sensor,
                start_date=args.start_date,
                backfill_days=args.backfill_days,
                settings_obj=args.settings_obj,
                progress=lambda msg: print(f"  {msg}"),
            )
        except (RuntimeError, ValueError, httpx.HTTPError) as exc:
            print(f"FIRMS API ingest failed: {exc}", file=sys.stderr)
            return 3
        print(f"fetched {len(df)} hotspots from the NASA FIRMS API -> {out}")
        return 0

    from .ingest_firms import ingest

    df, out = ingest(
        Path(args.input), Path(args.out), is_fixture=args.fixture, settings_obj=args.settings_obj
    )
    label = " [SYNTHETIC FIXTURE]" if args.fixture else ""
    print(f"ingested {len(df)} hotspots{label} -> {out}")
    return 0


def _cmd_ingest_weather(args: argparse.Namespace) -> int:
    import pandas as pd

    from .geo import INDONESIA_BBOX
    from .ingest_weather import grid_stations, ingest_stations

    if args.stations:
        stations_df = pd.read_csv(args.stations)
        stations = stations_df.to_dict("records")
    elif args.grid:
        if args.grid < 2:
            print("--grid must be >= 2 (points per axis, inclusive)", file=sys.stderr)
            return 2
        bbox = (
            tuple(float(value) for value in args.bbox.split(","))
            if args.bbox
            else INDONESIA_BBOX
        )
        stations = grid_stations(bbox=bbox, grid=args.grid)
    else:
        print(
            "ingest-weather needs --stations, or --grid (with optional --bbox) "
            "to build an ERA5 point grid",
            file=sys.stderr,
        )
        return 2

    df, out = ingest_stations(
        stations,
        args.start,
        args.end,
        Path(args.out),
        settings_obj=args.settings_obj,
        pause_seconds=args.pause,
        max_retries=args.retries,
        checkpoint_dir=Path(args.checkpoint_dir) if args.checkpoint_dir else None,
    )
    print(f"ingested {len(df)} station-days over {len(stations)} stations -> {out}")
    return 0


def _cmd_ingest_aerosol(args: argparse.Namespace) -> int:
    from .ingest_aerosol import default_points, ingest_grid

    if args.grid < 1:
        print("--grid must be >= 1", file=sys.stderr)
        return 2
    kwargs: dict = {"grid": args.grid}
    if args.bbox:
        kwargs["bbox"] = tuple(float(v) for v in args.bbox.split(","))
    points = default_points(**kwargs)
    df, out = ingest_grid(
        points,
        args.start,
        args.end,
        Path(args.out),
        settings_obj=args.settings_obj,
        pause_seconds=args.pause,
        max_retries=args.retries,
    )
    print(f"ingested {len(df)} point-days over {len(points)} grid points -> {out}")
    return 0


def _cmd_ingest_power(args: argparse.Namespace) -> int:
    import pandas as pd

    from .ingest_power import ingest_stations

    stations_df = pd.read_csv(args.stations)
    stations = stations_df.to_dict("records")
    df, out = ingest_stations(
        stations,
        args.start,
        args.end,
        Path(args.out),
        settings_obj=args.settings_obj,
        pause_seconds=args.pause,
        max_retries=args.retries,
        checkpoint_dir=Path(args.checkpoint_dir) if args.checkpoint_dir else None,
    )
    print(f"ingested {len(df)} station-days over {len(stations)} stations -> {out}")
    return 0


def _cmd_ingest_polygons(args: argparse.Namespace) -> int:
    from .ingest_polygons import ingest_polygon_file

    df, report, out = ingest_polygon_file(
        Path(args.input),
        Path(args.out),
        source_dataset=args.source,
        boundary_type=args.boundary_type,
        license=args.license,
        vintage=args.vintage,
        treatment=args.treatment,
        settings_obj=args.settings_obj,
    )
    print(f"ingested {len(df)} polygons -> {out} (quality passed: {report.passed})")
    return 0 if report.passed else 2


def _cmd_fetch_concessions(args: argparse.Namespace) -> int:
    import json

    from .ingest_polygons import LICENSE_WARNING, SOURCE_QUERY_URLS, fetch_arcgis_features

    if not args.confirm_license:
        print(f"refusing: pass --confirm-license after reviewing terms.\n{LICENSE_WARNING}", file=sys.stderr)
        return 3

    query_url = args.query_url or SOURCE_QUERY_URLS[args.source]
    features = fetch_arcgis_features(
        query_url,
        page_size=args.page_size,
        max_records=args.max_records,
        confirm_license=True,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1), encoding="utf-8")
    print(f"fetched {len(features)} features from {query_url} -> {out}")
    print(f"NOTE: {LICENSE_WARNING}")
    return 0


def _cmd_build_features(args: argparse.Namespace) -> int:
    from .build_features import build_and_save

    features, out = build_and_save(
        Path(args.polygons),
        Path(args.hotspots),
        Path(args.weather) if args.weather else None,
        args.as_of,
        Path(args.out),
        aerosol_path=Path(args.aerosol) if args.aerosol else None,
        settings_obj=args.settings_obj,
    )
    print(f"built {len(features)} feature rows as_of {args.as_of} -> {out}")
    return 0


def _cmd_run_exposure(args: argparse.Namespace) -> int:
    from .run_exposure import CAVEAT, run_exposure

    exposure, summary, _ = run_exposure(
        Path(args.polygons),
        Path(args.hotspots),
        args.as_of,
        Path(args.out),
        Path(args.out_public),
        settings_obj=args.settings_obj,
    )
    print(f"exposure rows: {len(exposure)} | summary: {summary}")
    print(f"CAVEAT: {CAVEAT}")
    return 0


def _cmd_run_forecast(args: argparse.Namespace) -> int:
    from .run_forecasts import DISCLAIMER, run_forecast

    df, out = run_forecast(Path(args.features), Path(args.out), settings_obj=args.settings_obj)
    print(f"forecast rows: {len(df)} -> {out}")
    print(f"DISCLAIMER: {DISCLAIMER}")
    return 0


def _cmd_make_fixtures(args: argparse.Namespace) -> int:
    from .fixtures import FIXTURE_NOTICE, fixture_hotspots

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    center = tuple(float(v) for v in args.center.split(",")) if args.center else (113.0, -2.0)
    df = fixture_hotspots(n=args.n, center=(center[0], center[1]))
    out = out_dir / "fixture_hotspots.csv"
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} SYNTHETIC FIXTURE hotspot rows -> {out} (center lon,lat = {center})")
    print(f"NOTICE: {FIXTURE_NOTICE}")
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    """Ad-hoc analytical queries over processed Parquet outputs via DuckDB.

    The optional ``spatial`` extension (official DuckDB extension, installed at
    runtime - no pip package) enables ST_* functions and a ``dataset_geo`` view
    with a decoded geometry column. Without it, ``dataset`` still works and
    ``geometry`` is available as WKT text.
    """
    import duckdb

    con = duckdb.connect(database=":memory:")
    spatial = False
    try:
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
        spatial = True
    except Exception:  # noqa: BLE001, S110 - offline/blocked is fine: text queries still work
        pass
    try:
        if args.file:
            escaped = str(Path(args.file)).replace("'", "''")
            con.execute(
                # the only interpolation here is the SQL-quote-escaped local path above
                f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{escaped}')"  # nosec B608
            )
            if spatial:
                try:
                    con.execute(
                        "CREATE VIEW dataset_geo AS "
                        "SELECT *, ST_GeomFromText(geometry) AS geom FROM dataset"
                    )
                except Exception:  # noqa: BLE001 - this file has no WKT geometry column
                    print(
                        "note: no WKT 'geometry' column in this file; view 'dataset_geo' unavailable",
                        file=sys.stderr,
                    )
        result = con.execute(args.sql).fetchdf()
    finally:
        con.close()
    if args.sql.upper().lstrip().startswith("SELECT") and "ST_" in args.sql.upper() and not spatial:
        print("note: duckdb spatial extension unavailable; ST_* functions will fail", file=sys.stderr)
    print(result.to_string(index=False) if len(result) else "(no rows)")
    return 0


def _cmd_quality(args: argparse.Namespace) -> int:
    from .quality import (
        validate_aerosol,
        validate_exposure,
        validate_features,
        validate_forecast,
        validate_hotspots,
        validate_polygons,
        validate_weather,
    )

    passed = True
    for path in args.datasets:
        p = Path(path)
        df = read_parquet(p)
        if "hotspot_id" in df.columns:
            report = validate_hotspots(df, dataset=str(p))
        elif "geometry" in df.columns:
            report = validate_polygons(df, dataset=str(p))
        elif "hazard_score" in df.columns:
            report = validate_forecast(df, dataset=str(p))
        elif "hotspot_count_in_polygon_30d" in df.columns:
            report = validate_exposure(df, dataset=str(p))
        elif "hotspot_count_7d" in df.columns:
            report = validate_features(df, dataset=str(p))
        elif "aerosol_optical_depth_mean" in df.columns:
            report = validate_aerosol(df, dataset=str(p))
        else:
            report = validate_weather(df, dataset=str(p))
        status = "PASS" if report.passed else "FAIL"
        print(f"[{status}] {p}: " + "; ".join(f"{c.name}={'ok' if c.passed else c.count}" for c in report.checks))
        passed = passed and report.passed
    return 0 if passed else 2


def build_parser(settings_obj: Settings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="haze-pipelines", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest-firms", help="Ingest NASA FIRMS hotspots (local CSVs or live API)")
    p.add_argument(
        "--input",
        default=str(settings_obj.raw_dir / "firms"),
        help="Directory of FIRMS CSVs (ignored with --from-api)",
    )
    p.add_argument("--out", default=str(settings_obj.processed_dir / "fire_hotspots.parquet"))
    p.add_argument(
        "--fixture",
        action="store_true",
        help="Mark inputs as SYNTHETIC FIXTURE data (never use for real observations)",
    )
    p.add_argument(
        "--from-api",
        action="store_true",
        help="Pull automatically from the NASA FIRMS API (requires FIRMS_API_KEY)",
    )
    p.add_argument(
        "--area",
        default=None,
        help="west,south,east,north bounding box (default: Indonesia)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=3,
        help="Trailing window in days, 1-5 (FIRMS area API per-request limit)",
    )
    p.add_argument(
        "--start-date",
        default=None,
        help="YYYY-MM-DD: pull a historical range starting here (chunked <=5-day windows)",
    )
    p.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help="Range length in days from --start-date (or, alone, trailing N days ending today)",
    )
    p.add_argument(
        "--sensor",
        default="MODIS_NRT",
        help="e.g. MODIS_NRT, VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, VIIRS_NOAA21_NRT",
    )
    p.set_defaults(func=_cmd_ingest_firms)

    p = sub.add_parser("make-fixture-hotspots", help="Write labeled synthetic hotspot CSVs for testing")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--n", type=int, default=12)
    p.add_argument("--center", default=None, help="lon,lat center for the fixture cluster")
    p.set_defaults(func=_cmd_make_fixtures)

    p = sub.add_parser("ingest-aerosol", help="Ingest CAMS haze/aerosol indicators (AOD/PM via Open-Meteo)")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--out", default=str(settings_obj.processed_dir / "haze_aerosol.parquet"))
    p.add_argument("--bbox", default=None, help="min_lon,min_lat,max_lon,max_lat (default: Indonesia)")
    p.add_argument("--grid", type=int, default=3, help="grid points per axis (CAMS is coarse, ~50 km)")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between grid points")
    p.add_argument("--retries", type=int, default=5, help="retries on HTTP 429")
    p.set_defaults(func=_cmd_ingest_aerosol)

    p = sub.add_parser(
        "ingest-power",
        help="Ingest NASA POWER / MERRA-2 daily weather (ERA5 fallback)",
    )
    p.add_argument("--stations", required=True, help="CSV with station_id,latitude,longitude columns")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between stations")
    p.add_argument("--retries", type=int, default=5, help="retries on HTTP 429")
    p.add_argument("--checkpoint-dir", default=None, help="resume completed stations")
    p.add_argument("--out", default=str(settings_obj.processed_dir / "weather.parquet"))
    p.set_defaults(func=_cmd_ingest_power)

    p = sub.add_parser("ingest-weather", help="Ingest Open-Meteo/ERA5 daily weather")
    p.add_argument(
        "--stations",
        default=None,
        help="CSV with station_id,latitude,longitude columns (omit to use --grid)",
    )
    p.add_argument(
        "--grid",
        type=int,
        default=None,
        help="build an ERA5 point grid with this many points per axis",
    )
    p.add_argument(
        "--bbox",
        default=None,
        help="min_lon,min_lat,max_lon,max_lat for --grid (default: Indonesia)",
    )
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument(
        "--pause",
        type=float,
        default=15.0,
        help="seconds between stations (Open-Meteo minutely quota)",
    )
    p.add_argument("--retries", type=int, default=5, help="retries on HTTP 429")
    p.add_argument(
        "--checkpoint-dir",
        default=None,
        help="write each completed station here and resume from it on a rerun",
    )
    p.add_argument("--out", default=str(settings_obj.processed_dir / "weather.parquet"))
    p.set_defaults(func=_cmd_ingest_weather)

    p = sub.add_parser("ingest-polygons", help="Normalize local concession/plantation GeoJSON")
    p.add_argument("--input", required=True)
    p.add_argument("--source", required=True, help="Source dataset name, e.g. BNPB_GlobalForestWatch2")
    p.add_argument("--boundary-type", required=True, choices=["concession", "plantation", "mill", "other"])
    p.add_argument("--license", required=True, help="Licence text/terms for the source dataset")
    p.add_argument("--vintage", default=None, help="Data vintage year or date")
    p.add_argument("--treatment", default="real-restricted", choices=["real-restricted", "synthetic-fixture"])
    p.add_argument("--out", default=str(settings_obj.processed_dir / "plantation_polygons.parquet"))
    p.set_defaults(func=_cmd_ingest_polygons)

    p = sub.add_parser(
        "fetch-concessions",
        help="Fetch concession/peatland polygons from ArcGIS services (license gate applies)",
    )
    p.add_argument("--source", default="bnpb", choices=["bnpb", "gfw", "gfw-peatlands"])
    p.add_argument("--query-url", default=None, help="Override the ArcGIS layer query URL")
    p.add_argument("--out", required=True)
    p.add_argument("--page-size", type=int, default=200)
    p.add_argument("--max-records", type=int, default=None)
    p.add_argument("--confirm-license", action="store_true")
    p.set_defaults(func=_cmd_fetch_concessions)

    p = sub.add_parser("build-features", help="Point-in-time environmental features")
    p.add_argument("--polygons", default=str(settings_obj.processed_dir / "plantation_polygons.parquet"))
    p.add_argument("--hotspots", default=str(settings_obj.processed_dir / "fire_hotspots.parquet"))
    p.add_argument("--weather", default=None)
    p.add_argument("--aerosol", default=None, help="CAMS haze/aerosol Parquet (optional)")
    p.add_argument("--as-of", required=True)
    p.add_argument("--out", default=str(settings_obj.processed_dir / "environmental_features.parquet"))
    p.set_defaults(func=_cmd_build_features)

    p = sub.add_parser("run-exposure", help="Hotspot x polygon exposure + anonymized public layer")
    p.add_argument("--polygons", default=str(settings_obj.processed_dir / "plantation_polygons.parquet"))
    p.add_argument("--hotspots", default=str(settings_obj.processed_dir / "fire_hotspots.parquet"))
    p.add_argument("--as-of", required=True)
    p.add_argument("--out", default=str(settings_obj.processed_dir / "exposure.parquet"))
    p.add_argument("--out-public", default=str(settings_obj.processed_dir / "exposure_public.geojson"))
    p.set_defaults(func=_cmd_run_exposure)

    p = sub.add_parser("run-forecast", help="Baseline hazard scores (labeled baseline, not a model)")
    p.add_argument("--features", default=str(settings_obj.processed_dir / "environmental_features.parquet"))
    p.add_argument("--out", default=str(settings_obj.processed_dir / "forecast_baseline.parquet"))
    p.set_defaults(func=_cmd_run_forecast)

    p = sub.add_parser(
        "query",
        help="Run a DuckDB SQL query over processed Parquet (use read_parquet('path') or --file for view 'dataset')",
    )
    p.add_argument("--sql", required=True)
    p.add_argument("--file", default=None, help="Parquet file exposed as the view 'dataset'")
    p.set_defaults(func=_cmd_query)

    p = sub.add_parser("quality", help="Run data-quality checks over processed datasets")
    p.add_argument("datasets", nargs="+")
    p.set_defaults(func=_cmd_quality)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Fresh Settings on every invocation: honors HAZE_DATA_DIR and friends at
    # call time, so tests can isolate the provenance ledger via the environment.
    settings_obj = Settings()
    parser = build_parser(settings_obj)
    args = parser.parse_args(argv)
    args.settings_obj = settings_obj
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
