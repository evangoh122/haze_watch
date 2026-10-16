# Deployment Guide

Three things run: a local dev stack (Docker Compose), the demo container
(single image, currently hosted as a Hugging Face Space), and the Cloudflare
routing that puts the demo at `www.evangoh.com/haze-watch`.

## Local development (supported)

```bash
cp .env.example .env        # fill in FIRMS_API_KEY etc.
docker compose up --build   # PostGIS + FastAPI + React dev server
```

| Service | Port | Notes |
|---|---|---|
| db | 5432 | postgis/postgis:16-3.4, named volume `pgdata`; bound to 127.0.0.1 |
| backend | 8000 | uvicorn with reload; code mounted at `/app` |
| frontend | 5173 | Vite dev server (served at `/`, API proxied to the backend) |

The dev frontend runs at the **root** (`VITE_BASE_PATH` unset), so nothing about
the subpath deployment affects local development.

## Demo container (single image)

`deploy/hf-space/Dockerfile` builds one image: the React app is built in a Node
stage, then nginx serves it and proxies `/api` to uvicorn; supervisord runs both.

```bash
# Prerequisite: data/processed/ is gitignored, so the pipeline outputs must
# exist (or be copied in) before building - the Dockerfile COPYs them.
docker build -f deploy/hf-space/Dockerfile -t haze-watch .
docker run -p 7860:7860 haze-watch
# -> http://localhost:7860/haze-watch/
```

Key points:

- The frontend is built with `VITE_BASE_PATH=/haze-watch/`, so every asset URL
  and the API base (`/haze-watch/api/v1`) already carry the prefix. Pass
  `--build-arg VITE_BASE_PATH=/` to produce a root-served image instead.
- The image bakes the public pipeline outputs (the anonymized
  `exposure_public.geojson`, the summary, the fixtures-labelled hotspot file, the
  baseline forecast and the provenance registry). The real-restricted
  `plantation_polygons.parquet` is never copied in.
- Currently deployed as the Hugging Face Space `egoh33/haze-watch` (public, no
  secrets → the deterministic data-grounded chat fallback answers).

## Public routing: www.evangoh.com/haze-watch

A Cloudflare Worker handles only the `/haze-watch*` route and proxies to the
Space; the rest of the domain is untouched. Full steps, verification commands and
cost notes are in `deploy/cloudflare/README.md`.

`www.evangoh.com` is canonical — the apex `evangoh.com` returns **522** over
HTTPS on every path (a Cloudflare->origin failure specific to that hostname;
`www` reaches the same origin in ~0.3s). Link to `www` until the apex origin
route is fixed.

| Piece | Where |
|---|---|
| Route pattern | `www.evangoh.com/haze-watch*` (apex route kept as a fallback) |
| Worker | `deploy/cloudflare/worker.js`, `wrangler.toml` |
| Prefix handling | `deploy/hf-space/nginx.conf` (strips `/haze-watch`) |
| Subpath build | `frontend/vite.config.ts` (`base`), `src/main.tsx` (router basename), `src/lib/api.ts` (API base) |
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
