# Cloudflare routing: evangoh.com's backend API paths

Routes the backend API paths on `www.evangoh.com` to the two HF Spaces that
still carry their own backend, while every other request on the domain is
served directly by `evangoh-frontend`'s own origin — including the
non-API `/haze-watch/*` pages and assets, since `evangoh-frontend` bundles
its own copy of the Haze Watch app (imported during the frontend split).

`www` is the canonical host, not the bare apex: as of 2026-10-16 the apex
`evangoh.com` returns **522** over HTTPS on every path, because Cloudflare
cannot complete its connection to the origin for that hostname. The same
origin answers `www` in ~0.3s, so this is an apex-specific Cloudflare config
problem, not an app or Hugging Face problem. Until it is fixed, point every
link at `www`.

## How it works

```
browser ──► www.evangoh.com/...                   (Cloudflare, proxied)
                │
                ├─ /haze-watch/api/*  ──► Worker ──► egoh33-haze-watch.hf.space/api/*
                ├─ /api/*             ──► Worker ──► egoh33-auditable-filing-qa.hf.space/api/*
                └─ everything else    ──► evangoh-frontend's own origin
                                           (portfolio, RAG Workbench UI, and the
                                            bundled Haze Watch SPA at /haze-watch/*)
```

- The Worker is scoped to `/haze-watch/api*` and `/api*` only, so **every
  other request on the domain is untouched** — in particular, non-API
  `/haze-watch/*` requests are never intercepted; they fall through to
  evangoh-frontend's own origin, which serves that SPA itself.
- `/haze-watch/api/*` is rewritten to `/api/*` before reaching the
  haze_watch Space — that backend serves on `/api/v1/*`, not
  `/haze-watch/api/v1/*`.
- `/api/*` is passed through unchanged to the RAG Workbench Space.
- Because the browser only talks to `www.evangoh.com`, the `*.hf.space`
  origins never appear in the page, in links, or in devtools.

## Prerequisites

1. The domain is already on Cloudflare with proxied (orange-cloud) records for
   `evangoh.com` and `www.evangoh.com`. No new DNS record is needed.
2. `www.evangoh.com`'s HF custom domain points at the `evangoh-frontend`
   Space (set in that Space's own Settings → Domains on huggingface.co —
   not a Cloudflare or git-tracked setting).
3. The haze_watch and Auditable-Filing-QA Spaces serve `/api/*` directly
   (haze_watch currently via its own nginx stripping `/haze-watch/api/` to
   `/api/`; once that Dockerfile drops nginx and goes backend-only, its
   FastAPI app needs to serve `/api/*` itself on the Space's public port).

## Deploy the Worker

```bash
cd deploy/cloudflare
npx wrangler login          # once
npx wrangler deploy         # creates/updates the routes from wrangler.toml
```

Verify (use `www`; the apex 522s regardless of the Worker):

```bash
curl -sI  https://www.evangoh.com/haze-watch/              | head -1   # 200, evangoh-frontend's own origin
curl -s   https://www.evangoh.com/haze-watch/api/v1/health            # {"status":"ok"} via the Worker
curl -s   https://www.evangoh.com/api/health                          # RAG Workbench backend, via the Worker
curl -sI  https://www.evangoh.com/                          | head -1   # portfolio, unchanged
```

## Notes

- **Cost:** Workers Free (100,000 requests/day) is ample for a portfolio; no
  Cloudflare or Hugging Face payment is required for this setup.
- **Cold starts:** a sleeping free-tier Space takes a while to wake on the first
  hit. The Worker waits for the origin rather than failing fast.
- **Local testing without Cloudflare:** run the container and hit it directly —
  `docker build -f deploy/hf-space/Dockerfile . && docker run -p 7860:7860 <img>`,
  then open `http://localhost:7860/api/v1/health` (once the Dockerfile is
  backend-only, the Space no longer serves the frontend itself — test the
  frontend by running `evangoh-frontend` locally instead).
