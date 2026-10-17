/**
 * Cloudflare Worker: routes evangoh.com's backend paths to the two HF Spaces
 * that still carry their own backend — haze_watch (/haze-watch*) and the
 * RAG Workbench (/api*, used by the portfolio's RAG Workbench UI, now part
 * of evangoh-frontend which is static-only and has no backend of its own).
 *
 * TODO: this Worker is cross-cutting whole-domain routing config, not really
 * a haze_watch concern — it was extended here to fix a live /api* regression
 * quickly after the evangoh-frontend cutover. Consider moving deploy/cloudflare/
 * into the evangoh-frontend repo as the canonical home for this.
 *
 * Scope this Worker to `/haze-watch*` and `/api*` (and their `www` variants)
 * so every other request on the domain is untouched.
 *
 * /haze-watch/api/* is stripped to /api/* before reaching the haze_watch
 * Space, rather than left to that container's nginx (see
 * deploy/hf-space/nginx.conf's bare /api/ block, which this now relies on).
 * That's currently a no-op either way, since nginx still does the same
 * stripping itself — but once the haze_watch Space's Dockerfile drops
 * nginx/the frontend build stage and becomes backend-only, this is the only
 * remaining place the prefix gets stripped.
 *
 * /api/* is passed through unchanged to the RAG Workbench Space — that
 * backend already serves on exactly that path (no prefix to strip).
 *
 * Everything else under /haze-watch/* (static assets, SPA routes) is passed
 * through unchanged: the haze_watch container's nginx still owns that prefix.
 *
 * The browser only ever sees evangoh.com, which keeps the *.hf.space origins
 * out of the page (no direct host in links, iframes or devtools).
 */

const HAZE_WATCH_HOST = "egoh33-haze-watch.hf.space";
const HAZE_WATCH_API_PREFIX = "/haze-watch/api/";
const RAG_WORKBENCH_HOST = "egoh33-auditable-filing-qa.hf.space";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // /haze-watch -> /haze-watch/ so relative asset URLs resolve.
    if (url.pathname === "/haze-watch") {
      return Response.redirect(`${url.origin}/haze-watch/`, 301);
    }

    const target = new URL(request.url);
    target.protocol = "https:";

    if (url.pathname.startsWith(HAZE_WATCH_API_PREFIX)) {
      target.hostname = HAZE_WATCH_HOST;
      target.pathname = `/api/${url.pathname.slice(HAZE_WATCH_API_PREFIX.length)}`;
    } else if (url.pathname.startsWith("/haze-watch")) {
      target.hostname = HAZE_WATCH_HOST;
    } else {
      // Only reachable via the /api* route pattern.
      target.hostname = RAG_WORKBENCH_HOST;
    }

    const proxied = new Request(target, request);

    // A cold HF Space can take a while to wake; let Cloudflare wait rather than
    // surfacing a 524 on the first hit.
    return fetch(proxied);
  },
};
