import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Database,
  Flame,
  Layers,
  MapPin,
  Play,
  ShieldCheck,
  Wind,
} from 'lucide-react';
import { DisclaimerFooter } from '../components/Disclaimer';

const APP_URL = 'https://egoh33-haze-watch.hf.space';

export default function HazeWatch() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = 'Haze Watch - Geospatial climate risk for lenders';
  }, []);

  return (
    <div className="min-h-screen bg-background text-primary font-sans selection:bg-accent/20 selection:text-white flex flex-col">
      <header className="border-b border-border/40 bg-background/72 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-secondary hover:text-primary transition-colors bg-transparent border-0 cursor-pointer font-medium text-sm"
          >
            <ArrowLeft size={16} />
            Back to portfolio
          </button>
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md border border-accent/25 bg-accent/8 text-accent-bright">
            Case Study & App
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 md:py-16 flex flex-col gap-14">
        <section className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-10 lg:gap-14 items-end animate-in fade-in slide-in-from-bottom-3 duration-300">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="editorial-rule" />
              <span className="editorial-kicker">Haze Watch</span>
            </div>
            <div className="flex items-center gap-3 mb-5">
              <div className="p-2.5 bg-accent/8 border border-accent/15 rounded-xl text-accent">
                <Flame size={24} />
              </div>
              <p className="text-xs font-mono text-accent-bright m-0">Geospatial climate risk for lenders</p>
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-semibold tracking-tight leading-[0.98] text-primary m-0 max-w-3xl text-balance">
              Environmental hazard, traced to borrower cash flow.
            </h1>
            <p className="text-secondary text-base leading-8 font-light mt-7 max-w-3xl text-pretty">
              Haze Watch joins real NASA fire observations and reanalysis weather to concession
              geography, then runs auditable credit stress scenarios over the same numbers a credit
              memo would cite - with every dataset carrying its provenance and licence.
            </p>
            <div className="flex flex-wrap gap-4 mt-8">
              <a
                href="#live-app"
                className="fintech-button px-5 py-2.5 group inline-flex items-center gap-2"
              >
                <Play size={16} className="fill-white" />
                Try the app here
              </a>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border/80 hover:bg-surface-elevated/40 text-primary font-semibold transition-all duration-200 cursor-pointer"
              >
                <Layers size={16} />
                How it works
              </a>
            </div>
          </div>

          <aside className="product-glass-preview rounded-2xl p-5 relative overflow-hidden">
            <div className="absolute -right-10 -top-10 w-36 h-36 bg-accent/15 blur-3xl" />
            <div className="text-[11px] font-mono text-secondary mb-4">hazard readout</div>
            <div className="space-y-3">
              <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
                <div className="text-xs text-primary font-semibold mb-2">Concession polygon</div>
                <div className="h-2 w-5/6 rounded bg-white/10 mb-2" />
                <div className="h-2 w-2/3 rounded bg-white/8" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-accent/15 bg-accent/8 p-3">
                  <div className="text-[10px] text-accent-bright font-mono mb-3">detections 30d</div>
                  <div className="h-8 rounded bg-background/50" />
                </div>
                <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
                  <div className="text-[10px] text-secondary font-mono mb-3">weather</div>
                  <div className="h-8 rounded bg-background/50" />
                </div>
              </div>
              <div className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
                <div className="flex items-center justify-between text-[10px] font-mono text-secondary">
                  <span>hazard baseline</span>
                  <span className="text-accent-bright">labeled</span>
                </div>
              </div>
            </div>
          </aside>
        </section>

        <section id="live-app" className="scroll-mt-20 animate-in fade-in slide-in-from-bottom-4 duration-450">
          <div className="flex items-center gap-3 mb-7">
            <span className="editorial-rule" />
            <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-primary m-0">
              The app, right here.
            </h2>
          </div>
          <div className="rounded-2xl border border-border/60 bg-surface/40 overflow-hidden">
            <div className="flex items-center justify-between gap-3 border-b border-border/40 px-4 py-2.5">
              <div className="flex items-center gap-2 font-mono text-[11px] text-secondary">
                <span className="w-2 h-2 rounded-full bg-accent" />
                egoh33-haze-watch.hf.space
              </div>
              <button
                type="button"
                onClick={() => window.open(APP_URL, '_blank', 'noopener,noreferrer')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border/80 px-3 py-1.5 text-xs font-semibold text-primary transition-colors hover:border-accent/50 hover:bg-surface-elevated/40 cursor-pointer"
              >
                Open full screen
                <ArrowLeft size={13} className="rotate-180" />
              </button>
            </div>
            <iframe
              src={APP_URL}
              title="Haze Watch live app"
              loading="lazy"
              className="h-[680px] w-full border-0 bg-background"
            >
              <p className="p-6 text-sm text-secondary">
                The app cannot be embedded here.{' '}
                <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="text-accent">
                  Open it in a new tab
                </a>
                .
              </p>
            </iframe>
          </div>
        </section>

        <section className="scroll-mt-20 animate-in fade-in slide-in-from-bottom-4 duration-450">
          <div className="flex items-center gap-3 mb-7">
            <span className="editorial-rule" />
            <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-primary m-0">
              The risk link that rarely gets modeled end to end.
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[0.82fr_1.18fr] gap-6 items-start">
            <div className="rounded-2xl border border-red-500/15 bg-red-500/[0.035] p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 rounded-full blur-2xl pointer-events-none" />
              <div className="flex items-center gap-2 text-red-300 font-semibold mb-4 text-xs font-mono">
                <AlertTriangle size={15} />
                portfolio blind spot
              </div>
              <p className="text-sm text-secondary leading-7 mb-6 font-light">
                Banks and insurers hold plantation portfolios exposed to recurring wildfire and haze.
                Environmental hazard sits in one system, borrower financials in another, and the link
                between them is asserted rather than computed.
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-12 text-center p-1.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs font-mono font-semibold mt-0.5">
                    haz
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-primary">Hazard events</h4>
                    <p className="text-[11px] text-secondary/70 m-0">Fire detections and drought weather arrive as raw geospatial feeds.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-12 text-center p-1.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs font-mono font-semibold mt-0.5">
                    cash
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-primary">Borrower impact</h4>
                    <p className="text-[11px] text-secondary/70 m-0">Yield, working capital and debt service sit in financial models.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-12 text-center p-1.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs font-mono font-semibold mt-0.5">
                    book
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-primary">Portfolio concentration</h4>
                    <p className="text-[11px] text-secondary/70 m-0">Correlated concessions turn local fires into book-level surprises.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="product-glass-preview rounded-2xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-40 h-40 bg-accent/10 rounded-full blur-3xl pointer-events-none" />
              <div className="flex items-center gap-2 text-accent-bright font-semibold mb-4 text-xs font-mono">
                <CheckCircle size={15} />
                what the app makes visible
              </div>
              <p className="text-sm text-secondary leading-7 mb-6 font-light max-w-2xl">
                The platform treats the join itself as the product: detection counts per concession,
                exposure summaries, a labeled hazard baseline, and stress scenarios whose every ratio
                traces to a documented formula.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="glass-sm p-4">
                  <Flame size={15} className="text-accent-bright mb-3" />
                  <h4 className="text-xs font-semibold text-primary mb-1">Real observations</h4>
                  <p className="text-[11px] text-secondary/70 m-0 leading-relaxed">NASA FIRMS detections and reanalysis weather, per dataset licence.</p>
                </div>
                <div className="glass-sm p-4">
                  <MapPin size={15} className="text-accent-bright mb-3" />
                  <h4 className="text-xs font-semibold text-primary mb-1">Polygon exposure</h4>
                  <p className="text-[11px] text-secondary/70 m-0 leading-relaxed">Concession boundaries join detections as-of the observation window.</p>
                </div>
                <div className="glass-sm p-4">
                  <ShieldCheck size={15} className="text-accent-bright mb-3" />
                  <h4 className="text-xs font-semibold text-primary mb-1">Auditable stress</h4>
                  <p className="text-[11px] text-secondary/70 m-0 leading-relaxed">Scenario engines show the full calculation trace for every ratio.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-20 animate-in fade-in slide-in-from-bottom-5 duration-600">
          <div className="flex items-center gap-3 mb-7">
            <span className="editorial-rule" />
            <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-primary m-0">
              From satellite detections to a stress scenario.
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">01 / ingest</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Real environmental feeds</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">NASA FIRMS hotspot detections and ERA5/Open-Meteo reanalysis weather, each registered with source, licence, treatment and checksum in a provenance ledger.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">02 / join</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Concession geography</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Detections and weather meet concession boundaries (BNPB / Global Forest Watch) point-in-time, as-of the observation window - never future-leaking.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">03 / score</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Labeled hazard baseline</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">A deterministic 0-1 baseline per polygon and horizon (24-72h). Explicitly a baseline - not a calibrated probability and not a probability of default.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">04 / stress</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Credit & insurance scenarios</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Auditable scenario engines with full calculation traces, built on entirely synthetic commercial data that is labeled at every step.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">05 / answer</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Guardrailed analyst chat</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Answers only from loaded pipeline data, cites the datasets it used, and refuses claims the data cannot support.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <div className="text-[10px] font-mono text-accent-bright mb-3">06 / export</div>
              <h4 className="text-sm font-semibold text-primary mb-2">Durable history</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Runs export to a versioned history store with a manifest of exactly what left the machine - restricted geometry never does.</p>
            </div>
          </div>
        </section>

        <section className="scroll-mt-20 animate-in fade-in slide-in-from-bottom-6 duration-700">
          <div className="flex items-center gap-3 mb-7">
            <span className="editorial-rule" />
            <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-primary m-0">
              Evidence first, claims second.
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card rounded-2xl p-5">
              <Wind size={15} className="text-accent-bright mb-3" />
              <h4 className="text-sm font-semibold text-primary mb-2">Real environmental data</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Fire detections, reanalysis weather and concession boundaries are real sources, each carrying its licence and treatment in the provenance ledger.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <Database size={15} className="text-accent-bright mb-3" />
              <h4 className="text-sm font-semibold text-primary mb-2">Synthetic commercial data</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Every company, financial statement, bank exposure and insurance policy in the demo is entirely fictional and labeled synthetic - no real firm is depicted.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <ShieldCheck size={15} className="text-accent-bright mb-3" />
              <h4 className="text-sm font-semibold text-primary mb-2">Hazard scores are baselines</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Scores are deterministic labeled baselines (0-1). They are never probabilities of default, never calibrated forecasts, and no model accuracy is claimed.</p>
            </div>
            <div className="glass-card rounded-2xl p-5">
              <AlertTriangle size={15} className="text-accent-bright mb-3" />
              <h4 className="text-sm font-semibold text-primary mb-2">Detections are not burned area</h4>
              <p className="text-[11px] text-secondary/80 leading-relaxed m-0">Hotspot counts are satellite detections - not confirmed burned area, not fire severity, and not causation for any financial outcome.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
            <div className="rounded-2xl border border-border/60 bg-surface/60 p-5 text-center">
              <div className="text-2xl font-mono font-semibold text-accent-bright">300</div>
              <div className="text-[11px] text-secondary/70 mt-1">real concession polygons (BNPB/GFW sample run)</div>
            </div>
            <div className="rounded-2xl border border-border/60 bg-surface/60 p-5 text-center">
              <div className="text-2xl font-mono font-semibold text-accent-bright">24-72h</div>
              <div className="text-[11px] text-secondary/70 mt-1">hazard horizons</div>
            </div>
            <div className="rounded-2xl border border-border/60 bg-surface/60 p-5 text-center">
              <div className="text-2xl font-mono font-semibold text-accent-bright">46</div>
              <div className="text-[11px] text-secondary/70 mt-1">pipeline tests</div>
            </div>
          </div>
        </section>

        <section className="flex flex-col items-start gap-5">
          <div className="flex flex-wrap gap-1.5">
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">Geospatial</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">FastAPI</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">React</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">MapLibre</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">DuckDB</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 bg-surface-elevated border border-border text-secondary rounded">Hugging Face Spaces</span>
          </div>
          <button
            onClick={() => window.open(APP_URL, '_blank', 'noopener,noreferrer')}
            className="fintech-button px-5 py-2.5 group"
          >
            <Play size={16} className="fill-white" />
            Open the app
          </button>
        </section>
      </main>

      <DisclaimerFooter />
    </div>
  );
}
