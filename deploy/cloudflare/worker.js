/**
 * Cloudflare Worker: routes evangoh.com's API paths to the two HF Spaces
 * that still carry their own backend — haze_watch (/haze-watch/api*) and
 * the RAG Workbench (/api*, used by the portfolio's RAG Workbench UI, now
 * part of evangoh-frontend which is static-only and has no backend of its
 * own).
 *
 * TODO: this Worker is cross-cutting whole-domain routing config, not really
 * a haze_watch concern — consider moving deploy/cloudflare/ into the
 * evangoh-frontend repo as the canonical home for this.
 *
 * Scoped to `/haze-watch/api*` and `/api*` only (and their `www` variants,
 * see wrangler.toml) — everything else, including non-API /haze-watch/*
 * (the SPA pages/assets), is untouched and falls through to evangoh-frontend's
 * own origin, which bundles its own copy of the Haze Watch app.
 *
 * /haze-watch/api/* is stripped to /api/* before reaching the haze_watch
 * Space; that backend serves on /api/v1/*, not /haze-watch/api/v1/*.
 *
 * /api/* is passed through unchanged to the RAG Workbench Space — that
 * backend already serves on exactly that path (no prefix to strip).
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
    const target = new URL(request.url);
    target.protocol = "https:";

    if (url.pathname.startsWith(HAZE_WATCH_API_PREFIX)) {
      target.hostname = HAZE_WATCH_HOST;
      target.pathname = `/api/${url.pathname.slice(HAZE_WATCH_API_PREFIX.length)}`;
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
