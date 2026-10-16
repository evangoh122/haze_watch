# Geospatial Climate Risk Intelligence Platform

An AI-powered geospatial climate-risk intelligence prototype for banks and insurers.
It translates real wildfire and haze activity in Indonesia into illustrative credit and
insurance risk indicators, paired with **entirely synthetic** companies, financial
statements, bank exposures and insurance policies.

> **Research prototype.** This is not a production credit-rating or insurance-pricing
> system. All commercial and financial data is synthetic and must stay labeled as such.
> See `docs/governance.md` for the full disclaimer and data-handling rules.

## Live

- **App** — `https://www.evangoh.com/haze-watch` (the demo container behind a Cloudflare
  Worker; use `www`, the bare apex has no working origin route — see
  `deploy/cloudflare/README.md`)
- **Case studies** — `/projects/haze-watch` and `/projects/rag-workbench` on the same host
- **Hugging Face Space** — `egoh33/haze-watch` (public; without an LLM key the chat layer
  falls back to the deterministic, data-grounded answers)
- **FIRMS history store** (private dataset) — `egoh33/haze-watch-historical`

## Current status

| Area | Status |
|---|---|
| Repository structure and scaffolding | Done |
| Geospatial ingestion pipeline (`pipelines/`) | **Done — 75 tests passing** |
| FIRMS 25-year detection archive (2000-2026) | **Done — 9.6M detections in per-sensor/year GeoParquet** |
| Provenance registry + data-quality gates | **Done** |
| Concession download w/ license gate + anonymized export | **Done** |
| Point-in-time feature building (leakage-safe) | **Done** |
| Baseline hazard score (deterministic, labeled) | **Done — not a model** |
| Environment (Docker Compose, CI) | Wired; 4 GitHub Actions workflows (python, frontend, security, firms-ingest) |
| LLM chat layer (`backend/app/llm/`) | **Done — grounded chat API + UI panel** |
| DeepSeek / OpenAI-compatible provider | Wired; live calls need `LLM_API_KEY` (`scripts/deepseek_review.py` for reviews) |
| SCQA website + banking demo | **Done — landing narrative + working stress-test demo (26 frontend tests)** |
| Synthetic financial data engine | Stubs + skipped tests only |
| ML models (segmentation, forecasting) | Not implemented |
| Credit / insurance analytics | Stress engine done; insurance analytics planned |

The repository **does** now produce environmental observations: `pipelines/` builds a
versioned FIRMS archive (MODIS 2000+, VIIRS 2012+, per sensor and year, 60 files,
9.6M detections) which is what the `/haze-watch` case study's historical work reads.
What is still absent is model evaluation results and finished credit/insurance
analytics — ML phases are unimplemented and the financial side stays synthetic.
Status will be updated as phases land.

### FIRMS history coverage

| Sensor lane | Span | Files | Detections |
|---|---|---|---|
| `MODIS_SP` | 2000-2026 | 27 | 1,797,353 |
| `VIIRS_SNPP_SP` | 2012-2026 | 15 | 4,099,201 |
| `VIIRS_NOAA20_SP` | 2018-2026 | 9 | 1,599,459 |
| `VIIRS_NOAA21_SP` | 2023-2026 | 4 | 584,461 |
| `*_NRT` (recency, refreshed daily) | 2024-2026 | 5 | 1,542,120 |

No missing years. The `*_SP` (Standard Processing) lanes carry the archive; the `*_NRT`
lanes only serve their retention window and are kept fresh by the daily job — which is
why backfills must use the `*_SP` sources.

## Repository structure

```
haze_watch/
├── backend/            FastAPI + Pydantic + SQLAlchemy + PostGIS API
│   ├── app/
│   │   ├── api/v1/     REST endpoints (fires, forecasts, concessions, companies,
│   │   │               credit, insurance, portfolio, provenance)
│   │   ├── core/       Config, logging, security
│   │   ├── db/         Engine, session, declarative base
│   │   ├── models/     SQLAlchemy ORM models
│   │   ├── schemas/    Pydantic request/response schemas
│   │   └── services/   Hazard scoring, exposure, scenario engines
│   └── tests/          pytest unit and integration tests
├── frontend/           React + TypeScript + Tailwind + MapLibre GL JS
│   └── src/pages/      10 core dashboard pages
├── ml/                 Geospatial ML: features, models, training, evaluation
├── pipelines/          Batch ingestion and scheduled inference jobs
├── synthetic/          Synthetic financial / corporate / insurance data engine
├── data/               raw | interim | processed | synthetic (+ provenance metadata)
├── docs/               Architecture, data model, API contract, evaluation, licensing
└── .github/workflows/  CI: python, frontend, security (gitleaks), firms-ingest
```

## Quickstart (local)

```bash
cp .env.example .env
docker compose up --build       # PostgreSQL/PostGIS + FastAPI + React
make test                       # data guard + pytest (backend, pipelines, synthetic) + frontend
make ingest-firms               # ingest FIRMS CSVs from data/raw/firms (no key needed;
                                # FIRMS_API_KEY only enables live API fetch)
```

- API: http://localhost:8000 (OpenAPI at `/docs`)
- Dashboard: http://localhost:5173

## Implementation roadmap

Phases follow `project_profile.md` section 12:

1. **MVP** — FIRMS history, fire map, concession overlay, synthetic companies and
   statements, borrower dashboard, baseline hazard scoring, one credit stress scenario.
2. **Predictive ML** — XGBoost fire-escalation forecasting with spatial/temporal backtesting.
3. **Computer vision** — burned-area segmentation from multispectral imagery.
4. **Insurance analytics** — accumulation and hypothetical loss scenarios.
5. **Production engineering** — scheduling, monitoring, auth, observability.

## Documentation

- `docs/architecture.md` — system architecture and data flow
- `docs/data-model.md` — database schema
- `docs/api-contract.md` — API contract
- `docs/data-sources-and-licensing.md` — dataset provenance and licensing register
- `docs/model-evaluation.md` — evaluation methodology
- `docs/pipeline.md` — pipeline usage and the FIRMS history backfill
- `docs/deployment.md` — deployment guide (dev compose, demo container, public routing)
- `docs/hf-access.md` — Hugging Face datasets/Spaces and reviewer access
- `docs/governance.md` — research disclaimer and governance rules
- `docs/llm.md` — LLM chat layer (DeepSeek / OpenAI-compatible providers)

## Data policy (summary)

- Real: satellite hotspots, weather, land cover, peatland, published concession polygons.
- Synthetic: corporate ownership, financial statements, bank exposures, insurance
  policies, asset values. Never real company or bank data.
- No employer data, credentials, code or infrastructure may be used.
