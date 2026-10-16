/**
 * Cloudflare Worker: routes evangoh.com/haze-watch/* to the Haze Watch Space.
 *
 * Scope this Worker to the route `evangoh.com/haze-watch*` (and the `www`
 * variant) so every other request on the domain is untouched — the portfolio
 * keeps being served by its existing origin.
 *
 * The path is passed through unchanged: the container's nginx owns the
 * /haze-watch prefix (it strips it for the static files and for /api). See
 * deploy/hf-space/nginx.conf.
 *
 * The browser only ever sees evangoh.com, which keeps the *.hf.space origin
 * out of the page (no direct host in links, iframes or devtools).
 */

const ORIGIN_HOST = "egoh33-haze-watch.hf.space";

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

    const proxied = new Request(target, request);

    // A cold HF Space can take a while to wake; let Cloudflare wait rather than
    // surfacing a 524 on the first hit.
    return fetch(proxied);
  },
};
