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

## The edit

Replaces the **Enterprise infrastructure / Market data architecture notes**
(Blueprint) card in the "selected work" section with the **Haze Watch** card and
converts the two project cards to a **Swiper carousel** (`swiper/react` 14,
`A11y` + `Keyboard` + `Navigation` modules, one card per view, `rewind` so
prev/next wrap). The arrows are driven by the Navigation module; the dots stay
React-rendered from `onSlideChange` so the bespoke Tailwind styling and
`aria-current` are unchanged. Only `swiper/css` and `swiper/css/a11y` are
imported, so no default Swiper chrome leaks into the design. Swipe-on-touch and
ArrowLeft/ArrowRight come with it.

The inactive card is now **`inert`, `aria-hidden` and `tabIndex={-1}`**, applied
through `SwiperSlide`'s render function (`isActive`). Previously the clipped card
stayed focusable, so a keyboard user could tab to - and activate - a card that
was not visible (CodeRabbit finding on this PR). The card is sized and styled to
the RAG Workbench card's system so both read as one design.

## Routing

Both stories moved to wildcard-safe `/projects/*` paths, so each app can own its
clean URL:

| Story | Path | App |
|---|---|---|
| RAG Workbench | `/projects/rag-workbench` | keeps `/rag` |
| Haze Watch | `/projects/haze-watch` | `www.evangoh.com/haze-watch` |

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

## Review checklist (for DeepSeek / human)

- [ ] Copy accuracy (no unsupported claims, no employer references)
- [x] Demo URL `https://huggingface.co/spaces/egoh33/haze-watch` - deployed
      2026-10-16, public
- [ ] Layout: both project cards share one size system
      (`product-glass-preview ... min-h-[520px]`, equal `lg:grid-cols-2`
      columns); card is clickable with hover highlight
- [ ] Carousel: one card per view, arrows/dots/arrow-keys work, the inactive
      slide is inert and untabbable (verified in headless Chromium against the
      deployed bundle: 19/19 checks)

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
