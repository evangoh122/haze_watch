"""Produce the Haze Watch card edit for evangoh.com (PortfolioHome.tsx).

Replaces the "Enterprise infrastructure / Market data architecture notes"
(Blueprint) card in the selected-work section with the Haze Watch card, sized
and styled to match the RAG Workbench card exactly (same product-glass-preview
shell, min-h-[520px], p-6 sm:p-8, same type scale), and equalizes the section
grid columns so both cards render at the same size. The card is fully clickable
(whole-card onClick opens the Space, Enter/Space via keyboard, hover glow +
border highlight, cursor pointer).

Output (NOT uploaded here):
  deploy/site-update/PortfolioHome.tsx   full edited file
  deploy/site-update/PortfolioHome.patch unified diff against the live version

Usage:
    uv run python deploy/site-update/make_card_edit.py --source /path/to/PortfolioHome.tsx

The source is the LIVE PortfolioHome.tsx from the evangoh.com site repo
(egoh33/Auditable-Filing-QA). Pass --source, or set PORTFOLIO_HOME_SRC.

Stats shown on the card are project-verified facts only (300 real concession
polygons from the BNPB/GFW sample run, 24-72h forecast horizons, 46 pipeline
tests measured via `uv run pytest pipelines/tests`). No invented metrics, per
the portfolio's own disclaimer rules.
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path

OUT_DIR_DEFAULT = Path(__file__).resolve().parents[2] / "deploy" / "site-update"

# Sizing/styling mirrors the RAG Workbench card (product-glass-preview shell,
# min-h-[520px], p-6 sm:p-8, same header/box/tile/tag/CTA classes) so the two
# cards read as one system. Like the RAG card it navigates internally: clicking
# (or Enter/Space) opens the /haze-watch case-study page, with hover glow +
# border highlight. The page carries the "Open the app" button to the deployed
# app (https://egoh33-haze-watch.hf.space).
CARD = """            <div
              data-tour="project-card"
              onClick={() => navigate('/haze-watch')}
              onKeyDown={(event) => activateCardOnKeyDown(event, () => navigate('/haze-watch'))}
              role="button"
              tabIndex={0}
              className="product-glass-preview hover:border-accent/50 rounded-2xl transition-all duration-300 flex flex-col justify-between p-6 sm:p-8 relative group overflow-hidden cursor-pointer min-h-[520px]"
            >
              <div className="absolute top-0 right-0 w-40 h-40 bg-accent/10 rounded-full blur-3xl group-hover:bg-accent/15 transition-colors pointer-events-none" />
              <div>
                <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-accent/8 border border-accent/15 rounded-xl text-accent">
                      <Flame size={20} />
                    </div>
                    <div>
                      <h3 className="text-xl sm:text-2xl font-semibold text-primary tracking-tight">Haze Watch</h3>
                      <p className="text-[11px] font-mono text-accent-bright">Geospatial climate risk for lenders</p>
                    </div>
                  </div>
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-md border border-accent/20 bg-accent/8 text-accent-bright">
                    Case Study & App
                  </span>
                </div>

                <div className="mb-6 bg-background/42 border border-white/[0.06] rounded-xl p-4">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-accent-bright mb-3 font-mono">
                    why it exists
                  </div>
                  <p className="text-sm text-secondary leading-7 mb-4 font-light">
                    Banks and insurers hold plantation portfolios exposed to recurring wildfire and haze, yet the link from environmental hazard to borrower cash flow is rarely modeled end to end. Haze Watch joins real NASA fire observations to concession geography and runs auditable credit stress scenarios.
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-left">
                    <div className="bg-white/[0.035] border border-white/[0.06] rounded-lg p-3">
                      <div className="text-sm font-mono font-semibold text-accent-bright">300</div>
                      <div className="text-[10px] text-secondary/70">real concession polygons</div>
                    </div>
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-lg p-3">
                      <div className="text-sm font-mono font-semibold text-accent-bright">24-72h</div>
                      <div className="text-[10px] text-secondary/70">hazard horizons</div>
                    </div>
                    <div className="bg-white/[0.035] border border-white/[0.06] rounded-lg p-3">
                      <div className="text-sm font-mono font-semibold text-accent-bright">46</div>
                      <div className="text-[10px] text-secondary/70">pipeline tests</div>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-secondary leading-7 mb-6 font-light max-w-xl">
                  Real environmental data, entirely synthetic commercial data. Every credit ratio traces to a documented formula, every dataset carries its provenance and licence, and hazard scores are labeled baselines - never probabilities of default.
                </p>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="glass-sm p-3.5">
                    <div className="flex items-center gap-2 text-accent text-xs font-semibold mb-1">
                      <Flame size={13} />
                      Real fire observations
                    </div>
                    <p className="text-[11px] text-secondary/70 m-0">NASA FIRMS detections and ERA5 weather joined to concession geography</p>
                  </div>
                  <div className="glass-sm p-3.5">
                    <div className="flex items-center gap-2 text-accent text-xs font-semibold mb-1">
                      <ShieldCheck size={13} />
                      Auditable stress tests
                    </div>
                    <p className="text-[11px] text-secondary/70 m-0">Scenario engines with full calculation traces and guardrailed analyst chat</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-border/30 pt-5 mt-2 flex-wrap gap-3">
                <div className="flex flex-wrap gap-1.5 max-w-md">
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">Geospatial</span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">FastAPI</span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">React</span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">MapLibre</span>
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">DuckDB</span>
                </div>
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-accent group-hover:text-accent-bright transition-colors group-hover:underline">
                  View case study
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </div>"""


def edit(source: Path, out_dir: Path) -> Path:
    original = source.read_text(encoding="utf-8")
    text = original

    # 1) lucide imports: add Flame + ShieldCheck; drop Cpu (only the replaced
    #    card used it - an unused import breaks the site's typecheck).
    old_import = "import { Mail, ArrowRight, Cpu, Network, Database, Search, Sparkles } from 'lucide-react';"
    new_import = "import { Mail, ArrowRight, Network, Database, Search, Sparkles, Flame, ShieldCheck } from 'lucide-react';"
    assert old_import in text, "import line not found"
    text = text.replace(old_import, new_import)

    # 2) accessible names below sm: the visible labels hide on small screens, so
    #    LinkedIn/Contact need aria-labels like the GitHub link already has.
    linkedin_anchor = (
        '              href="https://www.linkedin.com/in/eevangoh/"\n'
        '              target="_blank"\n'
        '              rel="noopener noreferrer"\n'
    )
    assert linkedin_anchor in text, "LinkedIn anchor not found"
    text = text.replace(
        linkedin_anchor,
        linkedin_anchor
        + "              aria-label=\"Visit Evan Goh's LinkedIn profile\"\n"
        + "              title=\"LinkedIn\"\n",
    )
    contact_anchor = '              href="mailto:evangohsg@gmail.com"\n'
    assert contact_anchor in text, "Contact anchor not found"
    text = text.replace(
        contact_anchor,
        contact_anchor
        + "              aria-label=\"Contact Evan Goh\"\n"
        + "              title=\"Contact\"\n",
    )

    # 3) footer disclaimer must not contradict the card's synthetic-data label.
    old_footer = "All data is publicly sourced and not related to my work."
    new_footer = (
        "Environmental data is publicly sourced; demo companies and financial "
        "figures are synthetic. Not related to my work."
    )
    assert old_footer in text, "footer disclaimer not found"
    text = text.replace(old_footer, new_footer)

    # 4) equalize the two project-card columns (was 1.12fr / 0.88fr) so both
    #    cards render at the same width.
    old_grid = '<div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.12fr)_minmax(280px,0.88fr)] gap-5 lg:gap-6 max-w-5xl">'
    new_grid = '<div className="grid grid-cols-1 lg:grid-cols-2 gap-5 lg:gap-6 max-w-5xl">'
    assert old_grid in text, "projects grid not found"
    text = text.replace(old_grid, new_grid)

    # 5) replace the Enterprise infrastructure (Blueprint) card in place.
    start_marker = "            <div\n              onClick={() => navigate('/rag', { state: { initialView: 'stocks' } })}"
    cta_marker = "                  Explore charts"
    start = text.find(start_marker)
    assert start != -1, "Enterprise infrastructure card not found"
    cta = text.find(cta_marker, start)
    assert cta != -1, "Enterprise card CTA not found"
    end = text.find("\n            </div>\n", cta)
    assert end != -1, "Enterprise card end not found"
    text = text[:start] + CARD + "\n" + text[end + len("\n            </div>\n") :]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "PortfolioHome.tsx").write_text(text, encoding="utf-8")

    patch = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile="a/PortfolioHome.tsx",
            tofile="b/PortfolioHome.tsx",
        )
    )
    (out_dir / "PortfolioHome.patch").write_text(patch, encoding="utf-8")

    print(f"edited file written: {out_dir / 'PortfolioHome.tsx'}")
    print(f"patch written: {out_dir / 'PortfolioHome.patch'} ({len(patch.splitlines())} lines)")
    print(f"Haze Watch cards: {text.count('Geospatial climate risk for lenders')}")
    print(f"Enterprise cards left: {text.count('Market data architecture notes')}")
    print(f"min-h-[520px] cards: {text.count('min-h-[520px]')}")
    return out_dir / "PortfolioHome.tsx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=os.environ.get("PORTFOLIO_HOME_SRC"),
        help="path to the live PortfolioHome.tsx (or set PORTFOLIO_HOME_SRC)",
    )
    parser.add_argument("--out-dir", default=str(OUT_DIR_DEFAULT))
    args = parser.parse_args()
    if not args.source:
        raise SystemExit(
            "no source file: pass --source /path/to/PortfolioHome.tsx or set "
            "PORTFOLIO_HOME_SRC (the live file from the evangoh.com site repo)"
        )
    source = Path(args.source)
    if not source.is_file():
        raise SystemExit(f"source file not found: {source}")
    edit(source, Path(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
