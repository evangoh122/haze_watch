# Cloudflare routing: evangoh.com/haze-watch

Serves the Haze Watch app at `https://evangoh.com/haze-watch` while the rest of
the domain keeps serving the portfolio site.

## How it works

```
browser ──► evangoh.com/haze-watch/...            (Cloudflare, proxied)
                │
                │  Worker route: evangoh.com/haze-watch*
                ▼
         egoh33-haze-watch.hf.space/...           (HF Space, single container)
                │  nginx strips /haze-watch
                ├─► /app/frontend/dist            static SPA build
                └─► 127.0.0.1:8000                FastAPI (/api/v1/...)
```

- The Worker is scoped to the `/haze-watch*` route, so **every other request on
  the domain is untouched** — the portfolio origin is unaffected.
- The path is forwarded unchanged; the container's nginx owns the prefix
  (`deploy/hf-space/nginx.conf`).
- Because the browser only talks to `evangoh.com`, the `*.hf.space` origin never
  appears in the page, in links, or in devtools.

## Prerequisites

1. The domain is already on Cloudflare with proxied (orange-cloud) records for
   `evangoh.com` and `www.evangoh.com`. No new DNS record is needed.
2. The Space exists and serves the `/haze-watch/` path, i.e. it was built from
   `deploy/hf-space/Dockerfile` (which sets `VITE_BASE_PATH=/haze-watch/` and
   ships the matching `nginx.conf`).

## Deploy the Worker

```bash
cd deploy/cloudflare
npx wrangler login          # once
npx wrangler deploy         # creates/updates the route from wrangler.toml
```

Verify:

```bash
curl -sI  https://evangoh.com/haze-watch/            | head -1   # 200
curl -s   https://evangoh.com/haze-watch/api/v1/health            # {"status":"ok"}
curl -sI  https://evangoh.com/                       | head -1   # portfolio, unchanged
```

## Notes

- **Cost:** Workers Free (100,000 requests/day) is ample for a portfolio; no
  Cloudflare or Hugging Face payment is required for this setup.
- **Cold starts:** a sleeping free-tier Space takes a while to wake on the first
  hit. The Worker waits for the origin rather than failing fast.
- **Local testing without Cloudflare:** run the container and hit it directly —
  `docker build -f deploy/hf-space/Dockerfile . && docker run -p 7860:7860 <img>`,
  then open `http://localhost:7860/haze-watch/`.
