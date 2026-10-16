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
| `make_card_edit.py` | Reproducible generator of the edit (rerun after upstream changes) |

## The edit

Replaces the **Enterprise infrastructure / Market data architecture notes**
(Blueprint) card in the "selected work" section with the **Haze Watch** card.
The card is sized and styled to the RAG Workbench card's system so both read as
one design: `product-glass-preview` shell, `p-6 sm:p-8`, `min-h-[520px]`, same
type scale and tile/tag/CTA classes, and the section grid is equalized
(`lg:grid-cols-2`, was `1.12fr / 0.88fr`) so both cards render at the same
width. The card is fully clickable (whole-card click opens the Space,
Enter/Space keyboard activation, hover glow + border highlight, pointer
cursor), matching the RAG card's affordances.

The edit also carries three small fixes to the existing page: aria-labels on
the LinkedIn/Contact header links (their visible labels hide below `sm`, unlike
the GitHub link), a reworded footer disclaimer ("All data is publicly sourced"
contradicted the card's synthetic-data label), and the lucide import line (adds
Flame/ShieldCheck, drops Cpu - only the replaced card used it).

Card claims are project-verified facts only: 300 real concession polygons
(BNPB/GFW sample run), 24-72h hazard horizons, 46 pipeline tests (measured via
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
