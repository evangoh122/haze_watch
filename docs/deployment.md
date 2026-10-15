# Deployment Guide

> Status: outline only. Local Docker Compose is the supported path today; nothing has
> been deployed to a hosted environment yet.

## Local development (supported)

```bash
cp .env.example .env        # fill in FIRMS_API_KEY etc.
docker compose up --build   # PostGIS + FastAPI + React dev server
```

Services:

| Service | Port | Notes |
|---|---|---|
| db | 5432 | postgis/postgis:16-3.4, named volume `pgdata` |
| backend | 8000 | uvicorn with reload; code mounted at `/app` |
| frontend | 5173 | Vite dev server |

Migrations (to be added in Phase 1): `alembic upgrade head`.

## Production / demo targets (planned)

- Containerized FastAPI backend behind a TLS-terminating proxy.
- Static React build served from object storage or a static host.
- Managed PostgreSQL/PostGIS.
- Scheduled ingestion/inference via cron or a scheduler (no Kafka).
- Optional Hugging Face Spaces demo using a reduced public dataset with the synthetic
  commercial layer only.

## Security requirements

- Secrets only via environment variables or a secret manager; never in the frontend
  bundle or the repository.
- Rate limiting and input validation on all public endpoints.
- Only public or synthetic inputs in any demo.
- Research disclaimer visible in the UI.
