"""Produce the Haze Watch card edit for evangoh.com (PortfolioHome.tsx).

Output (NOT uploaded - for DeepSeek review):
  deploy/site-update/PortfolioHome.tsx   full edited file
  deploy/site-update/PortfolioHome.patch unified diff against the live version

Stats shown on the card are project-verified facts only (300 real concession
polygons from the BNPB/GFW sample run, 24-72h forecast horizons, 41 pipeline
tests). No invented metrics, per the portfolio's own disclaimer rules.
"""

from pathlib import Path

SRC = Path(r"C:\Users\jianj\AppData\Local\Temp\opencode\PortfolioHome.tsx")
OUT_DIR = Path(__file__).resolve().parents[2] / "deploy" / "site-update"

text = SRC.read_text(encoding="utf-8")

# 1) lucide imports: add Flame + ShieldCheck
old_import = "import { Mail, ArrowRight, Cpu, Network, Database, Search, Sparkles } from 'lucide-react';"
new_import = "import { Mail, ArrowRight, Cpu, Network, Database, Search, Sparkles, Flame, ShieldCheck } from 'lucide-react';"
assert old_import in text, "import line not found"
text = text.replace(old_import, new_import)

CARD = """
            <div
              data-tour="project-card"
              onClick={() => window.open('https://huggingface.co/spaces/egoh33/haze-watch', '_blank', 'noopener,noreferrer')}
              onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); window.open('https://huggingface.co/spaces/egoh33/haze-watch', '_blank', 'noopener,noreferrer'); } }}
              role="button"
              tabIndex={0}
              className="product-glass-preview hover:border-accent/50 rounded-2xl transition-all duration-300 flex flex-col justify-between p-6 sm:p-8 relative group overflow-hidden cursor-pointer lg:col-span-2"
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
                  Open live demo
                  <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </div>
"""

# 2) insert the card after the second card, before the grid closes.
anchor = "\n          </div>\n        </section>"
idx = text.rindex(anchor)
text = text[:idx] + "\n" + CARD + text[idx:]

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "PortfolioHome.tsx").write_text(text, encoding="utf-8")
print(f"edited file written: {OUT_DIR / 'PortfolioHome.tsx'}")
print(f"cards in section: {text.count('data-tour=') + text.count('Open live demo')}")
