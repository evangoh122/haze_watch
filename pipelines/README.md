# Ingestion and Inference Pipelines

Batch jobs (run manually in Phase 1, scheduled in Phase 5). No streaming/queueing
infrastructure unless measurable latency requirements justify it.

| Job | Command | Output |
|---|---|---|
| Fixture hotspots (testing) | `haze-pipelines make-fixture-hotspots` | labeled synthetic CSV |
| Fire hotspots | `haze-pipelines ingest-firms [--fixture]` | `data/processed/fire_hotspots.parquet` |
| Weather | `haze-pipelines ingest-weather` | `data/processed/weather.parquet` |
| Concessions fetch | `haze-pipelines fetch-concessions --source bnpb\|gfw\|gfw-peatlands` | GeoJSON (license gate) |
| Concessions normalize | `haze-pipelines ingest-polygons` | `data/processed/plantation_polygons.parquet` |
| Features | `haze-pipelines build-features` | `data/processed/environmental_features.parquet` |
| Exposure | `haze-pipelines run-exposure` | `exposure.parquet` + anonymized `exposure_public.geojson` |
| Baseline forecast | `haze-pipelines run-forecast` | `data/processed/forecast_baseline.parquet` |
| Quality checks | `haze-pipelines quality` | pass/fail per dataset |

Common requirements for every job:

- Normalize CRS to EPSG:4326 and timestamps to UTC on ingest.
- Record dataset provenance (see `data/metadata/datasets.yaml`).
- Store both `observation_time` and `available_time` for observations used in training.
- Deduplicate hotspots and validate polygon geometry (see testing plan in
  `project_profile.md` section 11).
