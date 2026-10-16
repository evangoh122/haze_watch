# evangoh.com update - Haze Watch project card (DEPLOYED 2026-10-16)

Landed on evangoh.com on 2026-10-16 together with the Space
(`egoh33/haze-watch`), via the Option B upload below. `PortfolioHome.tsx` in
the `egoh33/Auditable-Filing-QA` Space is the source of evangoh.com; this
folder holds the applied edit for the record. The stories were later moved to
`/projects/*` (see "Routing" below) and the carousel was rebuilt on Swiper.

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

One piece of the carousel lives outside this file - the sizing/scale rules are
in the site's `frontend/src/index.css` (see "Carousel CSS" below), because they
have to target Swiper's own `.swiper-slide` markup.

## The edit

Converts the "selected work" section to a **three-card Swiper carousel**
(`swiper/react` 14, `A11y` + `Keyboard` + `Navigation` modules) in **center
mode**: `slidesPerView={1.15}` + `spaceBetween={28}` + `centeredSlides`, so the
active card sits centred at ~87% of the container with a ~41px peek of the
neighbour, and `rewind` makes prev/next wrap at the ends. Arrows are driven by
the Navigation module; the dots stay React-rendered from `onSlideChange` so the
bespoke Tailwind styling and `aria-current` are unchanged, and their count comes
from `instance.slides.length` rather than a literal list. Only `swiper/css` and
`swiper/css/a11y` are imported, so no default Swiper chrome leaks into the
design. ArrowLeft/ArrowRight and touch dragging come with it. Cards stay flat -
the evidence-heavy content is not something a coverflow tilt should distort
(`effect="coverflow"` + the EffectCoverflow module is the alternative).

The three cards:

| Card | How it got there | Goes to |
|---|---|---|
| RAG Workbench | kept, re-pointed at `/projects/rag-workbench` | internal route |
| Haze Watch | replaces the **Enterprise infrastructure / Market data architecture notes** (Blueprint) card | `/projects/haze-watch` |
| Quant Platform | added (third slide) | `github.com/evangoh122/quant_platform_1` (external) |

The Quant Platform copy is taken only from that repository's own README and
status tables, which carry verification dates - 287M rows ingested (239M bronze),
5 data domains (market, options, SEC, COT, macro), 8+ Lakebase tables - and it
repeats the repo's own caveat that the signals are an untuned baseline with no
predictive edge claimed. Its card is an `<a>` rather than a div with `onClick`,
because the target is external: `target="_blank"` + `rel="noopener noreferrer"`
keeps middle-click/copy-link and native keyboard activation.

The inactive card is **`inert`, `aria-hidden` and `tabIndex={-1}`**, applied
through `SwiperSlide`'s render function (`isActive`). Previously the clipped card
stayed focusable, so a keyboard user could tab to - and activate - a card that
was not visible (CodeRabbit finding on this PR). Every card is sized and styled
to the RAG Workbench card's system so the three read as one design.

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
(BNPB/GFW sample run), 24-72h hazard horizons, 75 pipeline tests (measured via
`uv run pytest pipelines/tests`). No invented metrics. The test count was
corrected from 68 to 75 after the FIRMS long-backfill retry/checkpoint/backoff
work landed.

## Carousel CSS (`frontend/src/index.css`)

The page carries the markup (Swiper + the `haze-proj-swiper` hook class); the
sizing rules live in the site's `index.css`, because they have to target Swiper's
own `.swiper-slide` elements. They are deliberately **unlayered**: Tailwind 4 puts
utilities/components into cascade layers, `swiper/css` is imported unlayered, and
unlayered declarations beat layered ones regardless of specificity - the same
rules inside `@layer components` silently do nothing (Swiper's
`.swiper-slide { display: block }` keeps winning).

```css
.haze-proj-swiper .swiper-slide {
  height: auto;
  align-self: stretch;
  display: flex;
}

.haze-proj-swiper .swiper-slide > * {
  width: 100%;
  transition: scale 500ms ease, opacity 500ms ease;
}

.haze-proj-swiper .swiper-slide:not(.swiper-slide-active) > * {
  scale: 0.93;
  opacity: 0.7;
}
```

Why:

- The wrapper stretches its slides and each slide is a flex box with the card
  filling it, so **both cards are 634px**. Without it each card hugs its own
  content and the shorter one (RAG Workbench, 578px) renders smaller than the
  Haze Watch card (634px) - even when it is the selected card.
- The non-active card is scaled to 0.93 and dimmed to 0.7, so the selected card
  is visibly the bigger one: **634x887 active vs 590x825 side**, in both
  directions.

## Review checklist (for DeepSeek / human)

- [ ] Copy accuracy (no unsupported claims, no employer references)
- [x] Demo URL `https://huggingface.co/spaces/egoh33/haze-watch` - deployed
      2026-10-16, public
- [ ] Layout: all three project cards share one size system
      (`product-glass-preview ... min-h-[520px]`); card is clickable with hover
      highlight
- [ ] Carousel: center mode, the selected card full size and the neighbours
      scaled down (887x651 active vs 825x605 sides, equal 651px base height); the
      dots are derived from `instance.slides.length` (three of them); arrows,
      dots and arrow-keys work; the inactive slides are inert and untabbable; the
      Quant Platform card is a real anchor to its repo (`target="_blank"` +
      `rel="noopener noreferrer"`). Verified in headless Chromium against the
      deployed bundle: 13/13 checks.

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
