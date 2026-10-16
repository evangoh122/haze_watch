# evangoh.com update - Haze Watch project card (DEPLOYED 2026-10-16)

Landed on evangoh.com on 2026-10-16 together with the Space
(`egoh33/haze-watch`), via the Option B upload below. `PortfolioHome.tsx` in
the `egoh33/Auditable-Filing-QA` Space is the source of evangoh.com; this
folder holds the applied edit for the record.

## Contents

| File | What it is |
|---|---|
| `PortfolioHome.tsx` | Complete edited page (drop-in replacement) |
| `PortfolioHome.patch` | Unified diff against the live version |
| `HazeWatch.tsx` | The `/haze-watch` case-study page incl. the embedded live app |
| `make_card_edit.py` | Reproducible generator of the edit (rerun after upstream changes) |

## The edit

Replaces the **Enterprise infrastructure / Market data architecture notes**
(Blueprint) card in the "selected work" section with the **Haze Watch** card and
converts the two project cards to a **carousel**: one card per view on a
sliding track (`translateX` transform), with prev/next buttons and dot
indicators (aria-labeled, keyboard operable, `aria-current` on the active dot).
The card is sized and styled to the RAG Workbench card's system so both read as
one design. Like the RAG card, it navigates internally: clicking the card (or
Enter/Space) opens the **`/haze-watch` case-study page**.

The `/haze-watch` page is reworded around the project's **historical-data
focus** and marks the work as **in progress**: a pulsing "historical backfill
in progress" status chip, a "Historical data - in progress" section with the
true source depths (FIRMS MODIS 2000+/VIIRS 2012+, ERA5 1940+, CAMS aerosol
2022+ with the Earthdata options noted) and a "work in progress" note that the
figures reflect the current sample run, not the finished archive. Per review,
the page has **no direct `.hf.space` host and no iframe** - the CTA opens the
Hugging Face brand page, to be swapped to the self-hosted origin once the
consolidated container ships.

The edit also carries three small fixes to the existing page: aria-labels on
the LinkedIn/Contact header links (their visible labels hide below `sm`, unlike
the GitHub link), a reworded footer disclaimer ("All data is publicly sourced"
contradicted the card's synthetic-data label), and the lucide import line (adds
Flame/ShieldCheck, drops Cpu - only the replaced card used it).

The `/haze-watch` page itself is added to the site repo as
`frontend/src/pages/HazeWatch.tsx` with a route in `frontend/src/App.tsx`
(commit `b6bf2c8` on `egoh33/Auditable-Filing-QA`), mirroring `RagOverview`'s
structure and claim discipline (300 real concession polygons, 24-72h horizons,
46 pipeline tests; synthetic commercial data labeled; hazard scores are
baselines; detections are not burned area).

Card claims are project-verified facts only: 300 real concession polygons
(BNPB/GFW sample run), 24-72h hazard horizons, 68 pipeline tests (measured via
`uv run pytest pipelines/tests`). No invented metrics.

## Review checklist (for DeepSeek / human)

- [ ] Copy accuracy (no unsupported claims, no employer references)
- [x] Demo URL `https://huggingface.co/spaces/egoh33/haze-watch` - deployed
      2026-10-16, public
- [ ] Layout: both project cards share one size system
      (`product-glass-preview ... min-h-[520px]`, equal `lg:grid-cols-2`
      columns); card is clickable with hover highlight

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
