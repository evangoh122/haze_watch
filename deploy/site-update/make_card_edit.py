"""Produce the Haze Watch card edit for evangoh.com (PortfolioHome.tsx).

Replaces the "Enterprise infrastructure / Market data architecture notes"
(Blueprint) card with the Haze Watch card and converts the two project cards to
a CAROUSEL (one card per view, sliding track with prev/next buttons and dot
indicators, keyboard accessible with aria labels). Output (NOT uploaded here):

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

# The Haze Watch card content (RAG-card sizing: product-glass-preview shell,
# min-h-[520px], p-6 sm:p-8). Navigates internally to the /haze-watch
# case-study page like the RAG card navigates to /rag-overview.
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

CAROUSEL_OPEN = """          <div className="relative max-w-5xl">
            <div className="overflow-hidden">
              <div
                className="flex transition-transform duration-500 ease-out"
                style={{ transform: `translateX(-${projectSlide * 100}%)` }}
              >
                <div className="w-full shrink-0">"""

SLIDE_BOUNDARY_OLD = """            </div>

            <div
              onClick={() => navigate('/rag', { state: { initialView: 'stocks' } })}"""

SLIDE_BOUNDARY_NEW = """            </div>
              </div>

              <div className="w-full shrink-0">
            <div
              onClick={() => navigate('/rag', { state: { initialView: 'stocks' } })}"""

CAROUSEL_TAIL = """            </div>
              </div>
            </div>
          </div>
          <div className="mt-6 flex items-center justify-center gap-4" role="group" aria-label="Project carousel">
            <button
              type="button"
              aria-label="Previous project"
              onClick={() => setProjectSlide((s) => (s + 1) % 2)}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-border/80 bg-surface-elevated/40 text-secondary transition-colors hover:border-accent/50 hover:text-primary cursor-pointer"
            >
              ‹
            </button>
            <div className="flex items-center gap-2">
              {[0, 1].map((i) => (
                <button
                  key={i}
                  type="button"
                  aria-label={`Show project ${i + 1}`}
                  aria-current={projectSlide === i}
                  onClick={() => setProjectSlide(i)}
                  className={`h-2 rounded-full transition-all duration-200 cursor-pointer ${projectSlide === i ? 'w-6 bg-accent' : 'w-2 bg-border hover:bg-secondary'}`}
                />
              ))}
            </div>
            <button
              type="button"
              aria-label="Next project"
              onClick={() => setProjectSlide((s) => (s + 1) % 2)}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-border/80 bg-surface-elevated/40 text-secondary transition-colors hover:border-accent/50 hover:text-primary cursor-pointer"
            >
              ›
            </button>
          </div>
          </div>
        </section>"""


def edit(source: Path, out_dir: Path) -> Path:
    original = source.read_text(encoding="utf-8")
    text = original

    # 1) imports: useState for the carousel; lucide adds Flame + ShieldCheck and
    #    drops Cpu (only the replaced card used it - unused breaks typecheck).
    old_import = "import { Mail, ArrowRight, Cpu, Network, Database, Search, Sparkles } from 'lucide-react';"
    new_import = "import { Mail, ArrowRight, Network, Database, Search, Sparkles, Flame, ShieldCheck } from 'lucide-react';"
    assert old_import in text, "lucide import line not found"
    text = text.replace(old_import, new_import)

    old_react_import = "import type { KeyboardEvent } from 'react';"
    assert old_react_import in text, "react import line not found"
    text = text.replace(
        old_react_import, "import { useState } from 'react';\n" + old_react_import
    )

    # 2) carousel state
    old_nav = "  const navigate = useNavigate();"
    assert old_nav in text, "navigate declaration not found"
    text = text.replace(
        old_nav, old_nav + "\n  const [projectSlide, setProjectSlide] = useState(0);"
    )

    # 3) accessible names below sm: the visible labels hide on small screens, so
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

    # 4) footer disclaimer must not contradict the card's synthetic-data label.
    old_footer = "All data is publicly sourced and not related to my work."
    new_footer = (
        "Environmental data is publicly sourced; demo companies and financial "
        "figures are synthetic. Not related to my work."
    )
    assert old_footer in text, "footer disclaimer not found"
    text = text.replace(old_footer, new_footer)

    # 5) grid -> carousel shell (outer > overflow-hidden > sliding track > slide 1)
    old_grid = '          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.12fr)_minmax(280px,0.88fr)] gap-5 lg:gap-6 max-w-5xl">'
    assert old_grid in text, "projects grid not found"
    text = text.replace(old_grid, CAROUSEL_OPEN)

    # 6) close slide 1 / open slide 2 between the two cards
    assert SLIDE_BOUNDARY_OLD in text, "card boundary not found"
    text = text.replace(SLIDE_BOUNDARY_OLD, SLIDE_BOUNDARY_NEW)

    # 7) replace the Enterprise infrastructure (Blueprint) card with Haze Watch
    start_marker = "            <div\n              onClick={() => navigate('/rag', { state: { initialView: 'stocks' } })}"
    cta_marker = "                  Explore charts"
    start = text.find(start_marker)
    assert start != -1, "Enterprise infrastructure card not found"
    cta = text.find(cta_marker, start)
    assert cta != -1, "Enterprise card CTA not found"
    end = text.find("\n            </div>\n", cta)
    assert end != -1, "Enterprise card end not found"
    text = text[:start] + CARD + "\n" + text[end + len("\n            </div>\n") :]

    # 8) close the carousel after the second card and add the controls
    tail_old = "            </div>\n          </div>\n        </section>"
    cta = text.find("                  View case study")
    assert cta != -1, "Haze card CTA not found"
    tail_at = text.find(tail_old, cta)
    assert tail_at != -1, "projects section tail not found"
    text = text[:tail_at] + CAROUSEL_TAIL + text[tail_at + len(tail_old) :]

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
    print(f"carousel markers: slides={text.count('w-full shrink-0')}, dots={text.count('Show project')}")
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
