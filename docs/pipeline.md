# Data Pipeline

> Status: **implemented and tested** (36 unit/integration tests passing). Forecasting
> is a labeled baseline; ML models arrive in Phase 2.

Package: `pipelines/` (installable as `haze-pipelines`, uv workspace member).
All commands run via `uv run haze-pipelines ...` from the repository root.

## Job graph

```
NASA FIRMS CSV exports ─┐
                        ├─> ingest-firms ───────────┐
(make-fixture-hotspots) ┘   [fixture flag]           │
                                                     │
Open-Meteo / ERA5 ────────> ingest-weather ──────────┤
                                                     ├─> build-features ─> run-forecast
BNPB / GFW ArcGIS ────────> fetch-concessions ──┐    │   (point-in-time)    (baseline)
local GeoJSON/GeoPackage ─> ingest-polygons ────┴────┴─> run-exposure
                                                    │     (spatial join)
                                                    └─> quality (data-quality gates)
```

## Commands

```bash
uv sync                                                    # install workspace

# 1. Real concession polygons (license gate applies)
uv run haze-pipelines fetch-concessions --source bnpb --max-records 300 \
    --out data/raw/concessions/bnpb_gfw_2026.geojson --confirm-license
uv run haze-pipelines ingest-polygons --input data/raw/concessions/bnpb_gfw_2026.geojson \
    --source BNPB_GlobalForestWatch2 --boundary-type concession \
    --license "GFW custom licence - verify before redistribution" --vintage 2025 \
    --treatment real-restricted --out data/processed/plantation_polygons.parquet

# 2. Fire hotspots - automatic pull (needs a free FIRMS_API_KEY), local CSVs, or fixtures
uv run haze-pipelines ingest-firms --from-api --days 3 --out data/processed/fire_hotspots.parquet
# historical backfill: walks <=5-day DATE-anchored windows from --start-date
# (dedup across windows; NRT processing recorded in provenance - use the FIRMS
# Archive Download Tool + --input for SP archive quality)
uv run haze-pipelines ingest-firms --from-api --start-date 2015-06-01 --backfill-days 120 \
  --sensor VIIRS_SNPP_NRT --out data/processed/fire_hotspots.parquet
# 2b. Haze/aerosol indicators (CAMS via Open-Meteo) - FIRMS is fire, NOT haze.
# NOTE: this route's archive starts 2022-08-31; deeper haze history needs NASA
# Earthdata (OMPS Aerosol Index 2012+ / MODIS MAIAC AOD 2000+).
uv run haze-pipelines ingest-aerosol --start 2023-01-01 --end 2023-03-31 --grid 3
uv run haze-pipelines ingest-firms --from-api --area 95,-6,120,6 --sensor VIIRS_SNPP_NRT \
    --out data/processed/fire_hotspots.parquet
uv run haze-pipelines ingest-firms --input data/raw/firms --out data/processed/fire_hotspots.parquet
uv run haze-pipelines make-fixture-hotspots --out-dir data/raw/firms --n 40 --center 116.2,-2.2
uv run haze-pipelines ingest-firms --input data/raw/firms --fixture --out data/processed/fire_hotspots.parquet

# 3. Weather (real, public API)
uv run haze-pipelines ingest-weather --stations data/raw/stations.csv \
    --start 2026-01-01 --end 2026-01-31 --out data/processed/weather.parquet

# 4. Derived datasets (spatial: nearest weather station per polygon, hotspot
#    distances to polygon boundary, not centroid)
uv run haze-pipelines build-features --weather data/processed/weather.parquet --as-of 2026-02-01T00:00:00Z
uv run haze-pipelines run-exposure --as-of 2026-02-01T00:00:00Z
uv run haze-pipelines run-forecast --features data/processed/environmental_features.parquet

# 5. Data quality + audit
uv run haze-pipelines quality data/processed/*.parquet
uv run haze-pipelines query --file data/processed/exposure.parquet \
    --sql "SELECT boundary_type, sum(hotspot_count_in_polygon_30d) AS n FROM dataset GROUP BY 1"
uv run python scripts/check_data_not_tracked.py   # guard: no restricted data in git
```

## Geospatial SQL (DuckDB spatial extension)

No pip package needed: `haze-pipelines query` tries `INSTALL spatial; LOAD spatial;`
(official DuckDB extension, downloaded once and cached). When available, `--file`
exposes two views:

- `dataset` — the raw table (`geometry` is WKT text)
- `dataset_geo` — same rows plus `geom` as a DuckDB GEOMETRY (files with a WKT
  `geometry` column, e.g. `plantation_polygons.parquet`)

```bash
# Point-in-polygon: which real concessions contain synthetic fixture detections?
uv run haze-pipelines query --file data/processed/plantation_polygons.parquet --sql \
  "SELECT polygon_id FROM dataset_geo
   WHERE ST_Intersects(geom, ST_Point(116.2, -2.2))"
```

Caveats (this build of the extension):

- The WKT parser is `ST_GeomFromText` (not `ST_GeomFromWKT`).
- `ST_Area(geom)` on EPSG:4326 geometry returns **square degrees** - useless as
  area. Use the geodesic `area_ha` column, or reproject first.
- `ST_Read('file.geojson')` reads the public GeoJSON outputs directly.
- Without the extension (e.g. offline), `dataset` text queries still work and an
  `ST_*` query prints a clear note instead of failing silently.
- Our Parquet files store WKT + a custom `haze_geo` metadata key - this is **not**
  the GeoParquet spec. GeoPandas/QGIS see plain text `geometry`; convert with
  `geopandas.GeoSeries.from_wkt`. Files written by GeoPandas in true GeoParquet
  format are also readable (geometry arrives as WKB: `st_geomfromwkb`).

## The four connected datasets (MVP)

| Dataset | Command | Treatment |
|---|---|---|
| `plantation_polygons` | `ingest-polygons` / `fetch-concessions` | `real-restricted` |
| `fire_observations` | `ingest-firms` | `real` or `synthetic-fixture` |
| `haze_aerosol` | `ingest-aerosol` | `real` (CAMS via Open-Meteo; archive from 2022-08-31) |
| `environmental_features` | `build-features` | `real` (derived) |
| `synthetic_financial_exposures` | `synthetic/` engine (next) | `synthetic` |

## Governance rules enforced in code

- **License gate**: `fetch-concessions` refuses to download geometry without
  `--confirm-license` after reviewing terms. Public GIS visibility is not
  redistribution permission (see `docs/data-sources-and-licensing.md`).
- **Boundary distinction**: `boundary_type` separates `concession` (land allocated
  for development) from `plantation` (land actually planted).
- **Attribution uncertainty**: source `company`/`group_comp` fields are stored as
  `company_attribution`/`group_attribution` with
  `attribution_confidence = "unverified"` and are dropped from all public outputs.
- **Anonymized public layer**: `run-exposure` writes `exposure_public.geojson` with
  `poly_*` IDs, binned areas and geometry simplified + rounded to 4 decimals
  (~11 m) so exact concession boundaries cannot be reconstructed.
- **Fixture labeling**: `make-fixture-hotspots` rows carry
  `notes = "SYNTHETIC FIXTURE - not an environmental observation"` and
  `ingest-firms --fixture` marks every row `is_fixture=True`. Exposure summaries
  print an explicit `INPUT MIX` warning whenever fixture detections meet real
  geometry.
- **Point-in-time correctness**: features and exposure use only rows whose
  `available_time <= as_of` (FIRMS lag 3h, weather lag 48h). Unit tests prove
  future rows can never leak into features.
- **Spatial correctness**: hotspot proximity is measured to the polygon boundary
  (0 inside; else distance to nearest edge), never to the centroid - correct for
  large or elongated concessions. Weather features come from the nearest station
  only (station id + distance recorded); stations beyond
  `HAZE_WEATHER_MAX_DISTANCE_KM` (default 300 km) leave the features empty rather
  than borrowing distant weather.
- **Tracked-data guard**: `scripts/check_data_not_tracked.py` (run by `make test`
  and CI) fails the build if any raw/processed/synthetic data file - especially
  licence-restricted concession geometry - is tracked by git.

## Durable history store (Hugging Face)

Pipeline history is exported to a **private HF dataset**
(`egoh33/haze-watch-historical`) so runs survive local machine loss and agents
can reference them. Each run uploads to `runs/<run_id>/` with the same layout as
the local `data/` directory (`processed/`, `metadata/`, `MANIFEST.json`), so
runs accumulate instead of overwriting each other:

```bash
# push current pipeline outputs (NEVER includes real-restricted geometry)
uv run python scripts/export_history_to_hf.py --upload

# fetch the latest run (or --run <run_id>) for grounding / offline analysis
uv run python scripts/fetch_history_from_hf.py --dest data/hf_history
```

Governance: `plantation_polygons.parquet` is excluded from every upload (licence
requires verification before redistribution); `exposure.parquet` ships only in
reduced form (centroids rounded to ~11 km, nearest-distance to whole km, areas
bucketed to 500 ha - no exact concession coordinates); `exposure_public.geojson`
(anonymized, simplified) is the only concession-derived geometry exported. The
per-run `MANIFEST.json` records exactly what left the machine.

Historical FIRMS detections also accumulate as **GeoParquet** (WKB Point
geometry + OGC `geo` metadata - readable by DuckDB spatial, GeoPandas, QGIS)
under `history/fire_hotspots/sensor=SENSOR/year=YYYY.parquet` in the same
dataset, synced by
`.github/workflows/firms-ingest.yml` (daily rolling window; `workflow_dispatch`
runs full backfills, e.g. `start_date=2000-11-01 backfill_days=9500`). Year
files merge on `hotspot_id`, so re-runs and overlapping windows never
double-count:

```bash
uv run python scripts/sync_firms_history_to_hf.py --backfill-days 7
uv run python scripts/sync_firms_history_to_hf.py --start-date 2000-11-01 --backfill-days 9500
```

Agent integration: the analyst chat grounds on `LLM_DATA_DIR` - point it at
`data/hf_history` after `fetch_history_from_hf.py` to answer from historical
runs (see docs/llm.md).
- **Provenance**: every ingest registers source, licence, treatment, row count,
  observation window and SHA-256 checksum in `data/metadata/registry.json`.
- **Honest claims**: hotspot counts are detections, not burned area or causation;
  the forecast is a labeled deterministic baseline (0-1 hazard score), not a
  calibrated probability or a PD.

## Current end-to-end result (2026-02-01 run)

- 300 real concession polygons (BNPB/GFW mirror, quality gates passed)
- 124 real station-days of weather (Open-Meteo/ERA5)
- 40 labeled fixture detections → 5 polygons with detections
- 300 feature rows, 900 baseline forecast rows
- All outputs registered in `data/metadata/registry.json`

## Not yet implemented

- FIRMS API live fetch is now wired (`ingest-firms --from-api`) and unit-tested
  against a stubbed client, but has **not** been exercised against the live FIRMS API
  from this repository - that needs a free MAP_KEY. The API caps a request at 10 days,
  so longer backfills must be looped.
- MapBiomas land-cover and peatland ingestion (`gfw-peatlands` source is wired but
  the WRI query endpoint was returning HTTP 500 at last check)
- Scheduled execution: `.github/workflows/firms-ingest.yml` pulls daily and uploads the
  parquet as an artifact (requires the `FIRMS_API_KEY` repo secret; it skips cleanly
  when the secret is absent). Writing scheduled output into a database is Phase 5.
- Burned-area estimation from imagery — Phase 3
