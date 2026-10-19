# evangoh.com update - Haze Watch project card (DEPLOYED 2026-10-16)

Landed on evangoh.com on 2026-10-16 together with the Space
(`egoh33/haze-watch`), via the Option B upload below. `PortfolioHome.tsx` in
the `egoh33/Auditable-Filing-QA` Space is the source of evangoh.com; this
folder holds the applied edit for the record. The stories were later moved to
`/projects/*` (see "Routing" below) and the carousel became a stacked deck.

## Contents

| File | What it is |
|---|---|
| `PortfolioHome.tsx` | Complete edited page (drop-in replacement) |
| `PortfolioHome.patch` | Unified diff against the live version |
| `HazeWatch.tsx` | The `/haze-watch` case-study page (no iframe) |
| `make_card_edit.py` | Reproducible generator of the edit (rerun after upstream changes) |

`make_card_edit.py` is the source of truth for `PortfolioHome.tsx`: run it
against the pre-edit page (`da7e546:frontend/src/pages/PortfolioHome.tsx`) and
it reproduces the deployed file byte-for-byte, then writes the patch.

One piece of the deck lives outside this file - the placement rules (transforms,
opacity, filter, z-order, the reserved peek) are in the site's
`frontend/src/index.css` (see "Deck CSS" below), because they work off the
`data-offset` attribute the page writes.

## 2026-10-19 - historical panels backfilled

The `/haze-watch` page no longer says the weather panel is "next" or the haze
panel is "partial depth". The core historical panels are now built and
provenance-registered:

- **Weather:** 5-point coverage set over 110-120E, 4S-6N, 1981-2026 history;
  83,625 station-days. All 300 concessions are within 158 km of a coverage
  point. The set is k-means over concession representative points. The delivered
  panel uses NASA POWER/MERRA-2 because the free Open-Meteo ERA5 archive quota
  blocked the full sweep; the ERA5 ingest path remains in `pipelines/`.
- **Haze:** 121-point CAMS grid at 1 degree over the same region, 2022-08-31 to
  2026-10-18; 182,710 point-days. All 300 concessions are within 75 km.
- **Fire:** the existing 9.6M-detection FIRMS archive, 2000-2026.

The case-study page now marks weather and haze as complete panels, keeps
2015/2019 haze explicitly open (pre-2022 needs NASA Earthdata), and reframes
"in progress" around peat/land-cover, the event study and the financial join.
The deck card moves from **75** to **84** pipeline tests and names CAMS haze
alongside FIRMS and ERA5.

The page file here (`HazeWatch.tsx`) is the reviewable source; the live site is
the separate `egoh33/Auditable-Filing-QA` Space, so deploy it with the same
single-file upload pattern as the card after approval.

## The edit

Converts the "selected work" section to a **stacked card deck** - no carousel
library and no translating track. Every card sits in the same grid cell and is
placed purely by its **offset from the active index** (`data-offset`, written by
the page), so React owns one number and the CSS does the rest:

| offset | placement |
|---|---|
| `0` | front: full size, opaque, `filter: none` |
| `+1` / `-1` | `translateX(+/-40px) scale(0.94)`, `opacity 0.6`, `brightness(0.6)` |
| `+2` / `-2` | `translateX(+/-80px) scale(0.88)`, `opacity 0.3`, `brightness(0.6)` |
| beyond | `opacity 0`, `pointer-events: none` |

`transform-origin` is `right center` behind the front card (and `left center` on
the mirrored side), so the cards behind poke outwards rather than shrinking
inwards. Motion is declared once: transform, opacity and filter all transition
over `450ms cubic-bezier(0.22, 1, 0.36, 1)`.

The three cards:

| Card | How it got there | Goes to |
|---|---|---|
| RAG Workbench | kept, re-pointed at `/projects/rag-workbench` | internal route |
| Haze Watch | replaces the **Enterprise infrastructure / Market data architecture notes** (Blueprint) card | `/projects/haze-watch` |
| Quant Platform | added (third card) | `github.com/evangoh122/quant_platform_1` (external) |

The Quant Platform copy is taken only from that repository's own README and status
tables, which carry verification dates - 287M rows ingested (239M bronze), 5 data
domains (market, options, SEC, COT, macro), 8+ Lakebase tables - and it repeats the
repo's own caveat that the signals are an untuned baseline with no predictive edge
claimed. Its card is an `<a>` rather than a div with `onClick`, because the target
is external: `target="_blank"` + `rel="noopener noreferrer"` keeps middle-click,
copy-link and native keyboard activation working.

Interaction:

- **Arrows and dots** keep their markup; they now call `moveProject(-1|1)` and
  `setActiveProject(i)`. The dots are generated from `PROJECT_TITLES`, so adding a
  card adds its dot.
- **Clicking a card behind the front one brings it forward** - the wrapper is the
  control, labelled `Show <title>`. Clicking the front card still follows its own
  route or link.
- **Keyboard**: ArrowLeft/ArrowRight with the deck focused. **Swipe**: a horizontal
  drag of 45px or more moves one card, and a swipe that ends over a card no longer
  also fires that card's click.
- **Accessibility**: only the front card's content is interactive. Cards behind it
  are `inert` + `aria-hidden` (their wrapper is the control), and anything more than
  two positions back is `opacity 0` + `pointer-events: none`, so nothing invisible
  is reachable by keyboard.

`swiper` is removed from the site's `frontend/package.json`, and with it the
`swiper/css` imports and the bundle weight that came with them.

## Routing

Both stories moved to wildcard-safe `/projects/*` paths, so each app can own its
clean URL:

| Story | Path | App |
|---|---|---|
| RAG Workbench | `/projects/rag-workbench` | keeps `/rag` |
| Haze Watch | `/projects/haze-watch` | `www.evangoh.com/haze-watch` |
| Quant Platform | `github.com/evangoh122/quant_platform_1` | external repository (the app itself needs a Databricks workspace login) |

`/rag-overview` and `/haze-watch` remain as aliases. The app's CTA
(`APP_URL` in `HazeWatch.tsx`) is `https://www.evangoh.com/haze-watch` - `www`
is canonical because the bare apex returns 522 over HTTPS (see
`deploy/cloudflare/README.md`); no `.hf.space` host appears anywhere, and there
is no iframe.

The `/haze-watch` page is reworded around the project's **historical-data
focus** and marks the work as **in progress**: a pulsing "historical backfill
in progress" status chip, a "Historical data - in progress" section with the
true source depths (FIRMS MODIS 2000+/VIIRS 2012+, ERA5 1940+, CAMS aerosol
2022+ with the Earthdata options noted) and a "work in progress" note that the
figures reflect the current sample run, not the finished archive.

The edit also carries three small fixes to the existing page: aria-labels on
the LinkedIn/Contact header links (their visible labels hide below `sm`, unlike
the GitHub link), a reworded footer disclaimer ("All data is publicly sourced"
contradicted the card's synthetic-data label), and the lucide import line (adds
Flame/ShieldCheck, drops Cpu - only the replaced card used it).

The `/haze-watch` page itself is added to the site repo as
`frontend/src/pages/HazeWatch.tsx` with a route in `frontend/src/App.tsx`
(commit `b6bf2c8` on `egoh33/Auditable-Filing-QA`), mirroring `RagOverview`'s
structure and claim discipline (300 real concession polygons, 24-72h horizons;
synthetic commercial data labeled; hazard scores are baselines; detections are
not burned area).

Card claims are project-verified facts only: 300 real concession polygons
(BNPB/GFW sample run), 24-72h hazard horizons, 84 pipeline tests (measured via
`uv run python -m pytest pipelines/tests`). No invented metrics. The test count
was corrected from 68 to 75 after the FIRMS long-backfill retry/checkpoint/backoff
work, then to 84 after the weather coverage/haze-feature work.

## Deck CSS (`frontend/src/index.css`)

The page carries the markup; the placement rules live in the site's `index.css`,
deliberately **unlayered** - Tailwind 4 puts utilities and components into cascade
layers, unlayered declarations outrank layered ones, so a layered version risks a
utility quietly winning.

```css
/* Stacked project deck ----------------------------------------------------------
   "Selected work" is a deck, not a track: every card sits in the same grid cell
   and is positioned purely by its offset from the active index - the page writes
   `data-offset` and this decides where the card goes. No library, no translate
   on a parent. The two cards behind poke out on the right (and the mirror on the
   left keeps the deck symmetric); anything further back is faded out entirely.

   Unlayered on purpose: layered utilities must not outrank these rules. */
.haze-deck {
  --deck-peek: 40px;
  --deck-peek-2: 80px;
  display: grid;
  /* the deck reserves the deepest peek on both sides, so the cards that poke out
     stay inside the layout instead of pushing the page sideways. The front card
     stays centred because the reservation is symmetric. */
  padding-inline: var(--deck-peek-2);
}

/* one cell for every card: the deck adopts the tallest card's height and each
   card stretches to it, so switching cards never resizes the section */
.haze-deck > * {
  grid-area: 1 / 1;
  align-self: stretch;
  transform-origin: right center;
  transition:
    transform 450ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 450ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 450ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform, opacity;
}

.haze-deck > [data-offset="0"] {
  transform: none;
  opacity: 1;
  filter: none;
  z-index: 30;
  /* the cards' surface is translucent glass, so without an opaque backing the
     cards stacked behind bleed through the front card's own text. Radius matches
     the card's rounded-2xl (1rem), so nothing square shows at the corners. */
  background: var(--color-background);
  border-radius: 1rem;
}

.haze-deck > [data-offset="1"] {
  transform: translateX(var(--deck-peek)) scale(0.94);
  opacity: 0.6;
  filter: brightness(0.6);
  z-index: 20;
}

.haze-deck > [data-offset="2"] {
  transform: translateX(var(--deck-peek-2)) scale(0.88);
  opacity: 0.3;
  filter: brightness(0.6);
  z-index: 10;
}

.haze-deck > [data-offset="-1"] {
  transform: translateX(calc(-1 * var(--deck-peek))) scale(0.94);
  opacity: 0.6;
  filter: brightness(0.6);
  z-index: 20;
  transform-origin: left center;
}

.haze-deck > [data-offset="-2"] {
  transform: translateX(calc(-1 * var(--deck-peek-2))) scale(0.88);
  opacity: 0.3;
  filter: brightness(0.6);
  z-index: 10;
  transform-origin: left center;
}

/* only ever seen mid-transition: three or more positions back is gone */
.haze-deck > [data-offset]:not([data-offset="0"]):not([data-offset="1"]):not([data-offset="-1"]):not([data-offset="2"]):not([data-offset="-2"]) {
  opacity: 0;
  pointer-events: none;
  z-index: 0;
}

/* the peek lives outside the deck box, so it has to fit the viewport */
@media (max-width: 1280px) {
  .haze-deck {
    --deck-peek: 20px;
    --deck-peek-2: 40px;
  }
}

@media (max-width: 900px) {
  .haze-deck {
    --deck-peek: 14px;
    --deck-peek-2: 28px;
  }
}

@media (max-width: 640px) {
  .haze-deck {
    --deck-peek: 10px;
    --deck-peek-2: 20px;
  }
}
```

Two details worth keeping:

- The deck **reserves the deepest peek as symmetric padding**, so the cards poking
  out are neither clipped nor able to push the page sideways. The first attempt did
  exactly that: 16px of horizontal overflow at a 1024px viewport.
- The front card gets an **opaque backing** (page background, 1rem radius). The
  card surface itself is translucent glass, so without it the cards stacked behind
  bled through the front card's own copy - caught by looking at a screenshot, not by
  a number.

## Review checklist (for DeepSeek / human)

- [ ] Copy accuracy (no unsupported claims, no employer references)
- [x] Demo URL `https://huggingface.co/spaces/egoh33/haze-watch` - deployed
      2026-10-16, public
- [ ] Layout: all three cards share one size system
      (`product-glass-preview ... min-h-[520px]`); the front card is clickable with
      hover highlight
- [ ] Deck: front card full size; `+/-1` at `translateX(+/-40px) scale(0.94)`
      `opacity 0.6`; `+/-2` at `+/-80px scale(0.88) opacity 0.3`, all with
      `brightness(0.6)` and a 450ms `cubic-bezier(0.22, 1, 0.36, 1)` transition
      (also on opacity and filter); clicking a back card brings it forward; arrows,
      dots (with `aria-current`), ArrowLeft/Right and swipe all move the deck; the
      hidden cards are inert and untabbable; the Quant Platform card is a real
      anchor to its repo (`target="_blank"` + `rel="noopener noreferrer"`); no
      horizontal overflow at 1440/1280/1024/900/390px. Verified in headless
      Chromium against the deployed bundle: 30/30 checks.

## Deploy procedure (after approval)

Option A - git (reviewable history):
```bash
git clone https://huggingface.co/spaces/egoh33/Auditable-Filing-QA
cd Auditable-Filing-QA
# copy PortfolioHome.tsx over frontend/src/pages/PortfolioHome.tsx
git add frontend/src/pages/PortfolioHome.tsx
git commit -m "portfolio: add Haze Watch project card"
git push   # space rebuilds; evangoh.com updates via Cloudflare
```

Option B - single-file upload (what was used):
```bash
uv run python -c "from huggingface_hub import HfApi; HfApi().upload_file(
  path_or_fileobj='deploy/site-update/PortfolioHome.tsx',
  path_in_repo='frontend/src/pages/PortfolioHome.tsx',
  repo_id='egoh33/Auditable-Filing-QA', repo_type='space',
  commit_message='portfolio: add Haze Watch project card')"
```

Deploying the Space rebuilds it - that is the moment evangoh.com changes.

