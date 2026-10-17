/**
 * Cloudflare Worker: routes evangoh.com/haze-watch/* to the Haze Watch Space.
 *
 * Scope this Worker to the route `evangoh.com/haze-watch*` (and the `www`
 * variant) so every other request on the domain is untouched — the portfolio
 * keeps being served by its existing origin.
 *
 * /haze-watch/api/* is stripped to /api/* here rather than left to the
 * container's nginx (see deploy/hf-space/nginx.conf's bare /api/ block,
 * which this now relies on). Today that's a no-op either way, since nginx
 * still does the same stripping itself — but once the haze_watch Space's
 * Dockerfile drops nginx/the frontend build stage and becomes backend-only,
 * this is the only remaining place the prefix gets stripped.
 *
 * Everything else under /haze-watch/* (static assets, SPA routes) is passed
 * through unchanged: the container's nginx still owns that prefix.
 *
 * The browser only ever sees evangoh.com, which keeps the *.hf.space origin
 * out of the page (no direct host in links, iframes or devtools).
 */

const ORIGIN_HOST = "egoh33-haze-watch.hf.space";
const API_PREFIX = "/haze-watch/api/";

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // /haze-watch -> /haze-watch/ so relative asset URLs resolve.
    if (url.pathname === "/haze-watch") {
      return Response.redirect(`${url.origin}/haze-watch/`, 301);
    }

    const target = new URL(request.url);
    target.protocol = "https:";
    target.hostname = ORIGIN_HOST;

    if (url.pathname.startsWith(API_PREFIX)) {
      target.pathname = `/api/${url.pathname.slice(API_PREFIX.length)}`;
    }

    const proxied = new Request(target, request);

    // A cold HF Space can take a while to wake; let Cloudflare wait rather than
    // surfacing a 524 on the first hit.
    return fetch(proxied);
  },
};
