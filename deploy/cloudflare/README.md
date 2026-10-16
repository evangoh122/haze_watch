# Cloudflare routing: www.evangoh.com/haze-watch

Serves the Haze Watch app at `https://www.evangoh.com/haze-watch` while the rest
of the domain keeps serving the portfolio site.

`www` is the canonical host, not the bare apex: as of 2026-10-16 the apex
`evangoh.com` returns **522** over HTTPS on every path, because Cloudflare cannot
complete its connection to the origin for that hostname. The same origin answers
`www` in ~0.3s, so this is an apex-specific Cloudflare config problem, not an app
or Hugging Face problem. Until it is fixed, point every link at `www`.

## How it works

```
browser ──► www.evangoh.com/haze-watch/...        (Cloudflare, proxied)
                │
                │  Worker route: www.evangoh.com/haze-watch*
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
- Because the browser only talks to `www.evangoh.com`, the `*.hf.space` origin
  never appears in the page, in links, or in devtools.

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

Verify (use `www`; the apex 522s regardless of the Worker):

```bash
curl -sI  https://www.evangoh.com/haze-watch/         | head -1   # 200
curl -s   https://www.evangoh.com/haze-watch/api/v1/health       # {"status":"ok"}
curl -sI  https://www.evangoh.com/                    | head -1   # portfolio, unchanged
```

## Notes

- **Cost:** Workers Free (100,000 requests/day) is ample for a portfolio; no
  Cloudflare or Hugging Face payment is required for this setup.
- **Cold starts:** a sleeping free-tier Space takes a while to wake on the first
  hit. The Worker waits for the origin rather than failing fast.
- **Local testing without Cloudflare:** run the container and hit it directly —
  `docker build -f deploy/hf-space/Dockerfile . && docker run -p 7860:7860 <img>`,
  then open `http://localhost:7860/haze-watch/`.
- **Known issue — the Space's own root URL:** `nginx.conf` relies on a relative
  redirect for `/` -> `/haze-watch/`, but nginx's `absolute_redirect` default is
  `on`, so it emits `http://<host>:7860/haze-watch/`. Port 7860 is not reachable
  from the internet, so a request to the Space root hangs. Fix: add
  `absolute_redirect off;` to the `server` block in `deploy/hf-space/nginx.conf`.
