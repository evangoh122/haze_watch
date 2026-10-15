# System Architecture and Data Flow

> Status: outline only. Diagrams and detailed design to be completed during Phase 1.

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React, TypeScript, Tailwind, MapLibre GL JS | 8 dashboard pages, maps, charts, scenario inputs |
| Backend API | FastAPI, Pydantic, SQLAlchemy | REST API, scenario calculations, provenance |
| Database | PostgreSQL + PostGIS | Observations, geometries, synthetic commercial data |
| ML / geospatial | PyTorch, scikit-learn, XGBoost, GeoPandas, Rasterio | Feature building, forecasting, segmentation |
| Ingestion | Scheduled Python batch jobs | FIRMS, weather, land cover, peatland, concessions |
| Experiment tracking | MLflow | Model versions, metrics, reproducibility |

## Data flow (target)

```
NASA FIRMS ─┐
ERA5/Meteo ─┤
Land cover ─┼─> pipelines/ingest_* ─> data/raw ─> normalize CRS + timestamps
Peatland ───┤                          │
Concessions ┘                          v
                                  data/processed (GeoParquet)
                                        │
              ┌─────────────────────────┼──────────────────────┐
              v                         v                      v
      ml/ (features, forecast,   backend/services       synthetic/ engine
       burned-area seg.)          (exposure, hazard)     (companies, financials,
              │                         │                 loans, policies)
              └────────────┬────────────┘                      │
                           v                                   v
                    PostgreSQL + PostGIS <─────────────────────┘
                           │
                           v
                  FastAPI /api/v1 ──> React dashboards
                           │
                           v
                  provenance + calculation traces
```

## Architectural decisions

- **Batch ingestion and scheduled inference**, not streaming. Kafka or real-time
  streaming is out of scope unless measurable latency requirements justify it.
- **PostGIS for spatial joins** (point-in-polygon, buffering, distance). GeoParquet
  for historical observation storage and offline ML feature work.
- **Hazard scoring kept separate from credit calibration.** Environmental hazard
  scores are never presented as validated PD estimates.
- **Synthetic commercial data generated offline** by a reproducible seeded engine,
  loaded into the database with explicit `is_synthetic` labeling.

## Open questions

- [ ] Auth model for Phase 5 (none in local dev).
- [ ] MLflow storage backend (local file vs. database).
- [ ] Whether Hugging Face Spaces demo uses a reduced public dataset subset.
