# Deployment Guide

Three things run: a local dev stack (Docker Compose), the demo container
(single image, currently hosted as a Hugging Face Space), and the Cloudflare
routing that puts the demo at `www.evangoh.com/haze-watch`.

## Local development (supported)

```bash
cp .env.example .env        # fill in FIRMS_API_KEY etc.
docker compose up --build   # PostGIS + FastAPI
```

| Service | Port | Notes |
|---|---|---|
| db | 5432 | postgis/postgis:16-3.4, named volume `pgdata`; bound to 127.0.0.1 |
| backend | 8000 | uvicorn with reload; code mounted at `/app` |

The frontend lives in the separate `evangoh-frontend` repo now — see its own
README for local dev setup. Point it at this backend's `http://localhost:8000`.

## Demo container (backend-only)

`deploy/hf-space/Dockerfile` builds a Python-only image: FastAPI/uvicorn
serves the API directly on the Space's public port. The frontend was
imported into `evangoh-frontend`, which serves `/haze-watch/*` itself in
production — this repo (including `docker-compose.yml`) is backend-only now,
`frontend/` has been removed entirely.

```bash
# Prerequisite: data/processed/ is gitignored, so the pipeline outputs must
# exist (or be copied in) before building - the Dockerfile COPYs them.
docker build -f deploy/hf-space/Dockerfile -t haze-watch .
docker run -p 7860:7860 haze-watch
# -> http://localhost:7860/api/v1/health
```

Key points:

- The app serves on `/api/v1/*` directly (`settings.api_prefix`) — no nginx,
  no prefix-stripping happens in this container anymore. The Cloudflare
  Worker does that instead (see below).
- The image bakes the public pipeline outputs (the anonymized
  `exposure_public.geojson`, the summary, the fixtures-labelled hotspot file, the
  baseline forecast and the provenance registry). The real-restricted
  `plantation_polygons.parquet` is never copied in.
- Currently deployed as the Hugging Face Space `egoh33/haze-watch` (public, no
  secrets → the deterministic data-grounded chat fallback answers).

## Public routing: www.evangoh.com/haze-watch

A Cloudflare Worker handles only `/haze-watch/api*` (and the separate
`/api*` rule for the RAG Workbench backend) and proxies to this Space;
every other request on the domain, including non-API `/haze-watch/*`
(the SPA pages/assets), is served directly by `evangoh-frontend`'s own
origin. Full steps, verification commands and cost notes are in
`deploy/cloudflare/README.md`.

`www.evangoh.com` is canonical — the apex `evangoh.com` returns **522** over
HTTPS on every path (a Cloudflare->origin failure specific to that hostname;
`www` reaches the same origin in ~0.3s). Link to `www` until the apex origin
route is fixed.

| Piece | Where |
|---|---|
| Route pattern | `www.evangoh.com/haze-watch/api*` (apex route kept as a fallback) |
| Worker | `deploy/cloudflare/worker.js`, `wrangler.toml` |
| Prefix handling | the Worker itself (`/haze-watch/api/` → `/api/`) |
| Non-API `/haze-watch/*` | served by `evangoh-frontend`'s own origin, not this Space |
| Subpath build (in `evangoh-frontend`) | `src/haze-watch/lib/api.ts` (API base) |
| App link | portfolio `HazeWatch.tsx` `APP_URL` = `https://www.evangoh.com/haze-watch` |

No Cloudflare or Hugging Face payment is required for this setup — the Worker
free tier covers it.

## Security requirements

- Secrets only via environment variables or a secret manager; never in the
  frontend bundle or the repository.
- Rate limiting and input validation on all public endpoints. **Note:** the demo
  Space is public; do not set `LLM_API_KEY` there without also adding a rate
  limit, or it becomes an open LLM proxy.
- Only public or synthetic inputs in any demo.
- Research disclaimer visible in the UI.
