# Geospatial Climate Risk Intelligence Platform

An AI-powered geospatial climate-risk intelligence prototype for banks and insurers.
It translates real wildfire and haze activity in Indonesia into illustrative credit and
insurance risk indicators, paired with **entirely synthetic** companies, financial
statements, bank exposures and insurance policies.

> **Research prototype.** This is not a production credit-rating or insurance-pricing
> system. All commercial and financial data is synthetic and must stay labeled as such.
> See `docs/governance.md` for the full disclaimer and data-handling rules.

## Current status

| Area | Status |
|---|---|
| Repository structure and scaffolding | Done |
| Geospatial ingestion pipeline (`pipelines/`) | **Done — 36 tests passing** |
| Provenance registry + data-quality gates | **Done** |
| Concession download w/ license gate + anonymized export | **Done** |
| Point-in-time feature building (leakage-safe) | **Done** |
| Baseline hazard score (deterministic, labeled) | **Done — not a model** |
| Environment (Docker Compose, CI) | Wired; runs test suites |
| LLM chat layer (`backend/app/llm/`) | **Done — grounded chat API + UI panel** |
| DeepSeek / OpenAI-compatible provider | Wired; live calls need `LLM_API_KEY` (`scripts/deepseek_review.py` for reviews) |
| SCQA website + banking demo | **Done — landing narrative + working stress-test demo (21 frontend tests)** |
| Synthetic financial data engine | Stubs + skipped tests only |
| ML models (segmentation, forecasting) | Not implemented |
| Credit / insurance analytics | Stress engine done; insurance analytics planned |

Nothing in this repository currently produces environmental observations, model
evaluation results, or finished analytics. Status will be updated as phases land.

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
│   └── src/pages/      8 core dashboard pages
├── ml/                 Geospatial ML: features, models, training, evaluation
├── pipelines/          Batch ingestion and scheduled inference jobs
├── synthetic/          Synthetic financial / corporate / insurance data engine
├── data/               raw | interim | processed | synthetic (+ provenance metadata)
├── docs/               Architecture, data model, API contract, evaluation, licensing
└── .github/workflows/  CI (backend tests, frontend build)
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
- `docs/deployment.md` — deployment guide
- `docs/governance.md` — research disclaimer and governance rules
- `docs/llm.md` — LLM chat layer (DeepSeek / OpenAI-compatible providers)

## Data policy (summary)

- Real: satellite hotspots, weather, land cover, peatland, published concession polygons.
- Synthetic: corporate ownership, financial statements, bank exposures, insurance
  policies, asset values. Never real company or bank data.
- No employer data, credentials, code or infrastructure may be used.
