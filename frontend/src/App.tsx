import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { API_BASE_URL } from "./lib/api";
import BankingDemo from "./pages/BankingDemo";
import ChatPage from "./pages/ChatPage";
import FireForecast from "./pages/FireForecast";
import Landing from "./pages/Landing";
import LiveFireMap from "./pages/LiveFireMap";
import ConcessionExposure from "./pages/ConcessionExposure";
import CompanyProfiles from "./pages/CompanyProfiles";
import CreditStressTest from "./pages/CreditStressTest";
import InsuranceAccumulation from "./pages/InsuranceAccumulation";
import ModelProvenance from "./pages/ModelProvenance";

interface NavEntry {
  to: string;
  label: string;
  icon: string;
  tag?: string;
  end?: boolean;
}

const MONITOR: NavEntry[] = [
  { to: "/", label: "Overview", icon: "◈", end: true },
  { to: "/map", label: "Live Fire Map", icon: "◉" },
  { to: "/forecast", label: "Fire Forecast", icon: "◔" },
];

const ANALYSIS: NavEntry[] = [
  { to: "/banking", label: "Banking Demo", icon: "▣" },
  { to: "/chat", label: "Analyst Chat", icon: "✎" },
];

const PLANNED: NavEntry[] = [
  { to: "/concessions", label: "Concessions", icon: "⬡", tag: "PLAN" },
  { to: "/companies", label: "Company Profiles", icon: "▤", tag: "PLAN" },
  { to: "/credit", label: "Stress Testing", icon: "◈", tag: "PLAN" },
  { to: "/insurance", label: "Insurance", icon: "◫", tag: "PLAN" },
  { to: "/provenance", label: "Provenance", icon: "◎", tag: "PLAN" },
];

function NavGroup({ label, entries }: { label: string; entries: NavEntry[] }) {
  return (
    <div>
      <p className="px-2 pb-2 pt-5 font-mono text-[10px] font-semibold uppercase tracking-[0.13em] text-[#8e9bae]">
        {label}
      </p>
      <nav className="flex flex-col gap-[3px]">
        {entries.map((entry) => (
          <NavLink
            key={entry.to}
            to={entry.to}
            end={entry.end}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            <span className="w-4 text-center text-[15px] leading-none">{entry.icon}</span>
            {entry.label}
            {entry.tag && (
              <em className="ml-auto rounded-full border border-border bg-surface-elevated/[0.06] px-2 py-[2px] font-mono text-[10px] not-italic text-secondary">
                {entry.tag}
              </em>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<"unknown" | "online" | "offline">("unknown");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/health`)
      .then((response) => {
        if (!cancelled) setHealth(response.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setHealth("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar (RAG workbench pattern): brand, workspace, nav, system card */}
      <aside className="hidden w-[248px] shrink-0 flex-col bg-navy px-[18px] pb-[18px] pt-[25px] text-[#dbe5f3] md:flex">
        <div className="flex items-center gap-[10px] px-2 pb-[34px]">
          <span className="grid h-[29px] w-[29px] place-items-center border border-[#c9a968] font-serif text-[17px] font-semibold text-gold">
            H
          </span>
          <span>
            <strong className="block text-[13px] font-semibold tracking-[0.18em] text-white">
              HAZE WATCH
            </strong>
            <span className="mt-[3px] block font-mono text-[10px] tracking-[0.16em] text-[#93a6bd]">
              CLIMATE RISK INTELLIGENCE
            </span>
          </span>
        </div>

        <a
          href="https://www.evangoh.com"
          className="mb-4 mt-[-18px] flex items-center gap-1.5 px-2 font-mono text-[10px] uppercase tracking-[0.13em] text-[#8e9bae] transition-colors hover:text-white"
        >
          ← Back to portfolio
        </a>

        <p className="px-[10px] pb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.13em] text-[#8e9bae]">
          Workspace
        </p>
        <button className="w-full rounded border border-[#304159] bg-[#12233a] px-[10px] py-[11px] text-left text-xs font-medium text-white">
          Indonesia · Wildfire &amp; haze
          <span className="float-right text-[#8ea1b7]">⌄</span>
        </button>

        <NavGroup label="Monitor" entries={MONITOR} />
        <NavGroup label="Analysis" entries={ANALYSIS} />
        <NavGroup label="Planned" entries={PLANNED} />

        <div className="flex-1" />
        <div className="border-t border-[#25364e] px-[10px] pt-4">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.13em] text-[#8e9bae]">
            System
          </p>
          <p className="mt-2 font-mono text-[11px] text-secondary">
            <span
              className={`mr-[7px] inline-block h-[7px] w-[7px] rounded-full ${
                health === "online"
                  ? "bg-bullish shadow-[0_0_0_3px_rgba(67,209,158,0.25)]"
                  : health === "offline"
                    ? "bg-bearish shadow-[0_0_0_3px_rgba(255,114,127,0.25)]"
                    : "bg-muted"
              }`}
            />
            {health === "online"
              ? "PIPELINE ONLINE"
              : health === "offline"
                ? "BACKEND UNREACHABLE"
                : "STATUS UNKNOWN"}
          </p>
          <p className="mt-1 font-mono text-[10px] text-[#6f7b8e]">
            model: persistence-baseline 0.1.0
          </p>
          <p className="font-mono text-[10px] text-[#6f7b8e]">research prototype · v0.1.0</p>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-surface-elevated px-6">
          <div className="flex items-center gap-2">
            <span className="grid h-[26px] w-[26px] place-items-center border border-[#c9a968] font-serif text-sm font-semibold text-gold md:hidden">
              H
            </span>
            <p className="eyebrow">Research prototype · real environmental data · synthetic commercial data</p>
          </div>
          <span className="rounded-full bg-amberbg px-[10px] py-1 font-mono text-[9px] font-semibold tracking-wide text-amber">
            SYNTHETIC COMMERCIAL DATA
          </span>
        </header>

        {/* Mobile tab nav */}
        <nav className="sticky top-16 z-10 flex overflow-x-auto border-b border-[#25364e] bg-navy md:hidden">
          {[...MONITOR, ...ANALYSIS].map((entry) => (
            <NavLink
              key={entry.to}
              to={entry.to}
              end={entry.end}
              className={({ isActive }) =>
                `whitespace-nowrap px-[14px] py-3 text-xs ${isActive ? "text-white" : "text-[#91a1b5]"}`
              }
            >
              {entry.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 px-6 py-6 md:px-[42px]">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/map" element={<LiveFireMap />} />
            <Route path="/forecast" element={<FireForecast />} />
            <Route path="/banking" element={<BankingDemo />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/concessions" element={<ConcessionExposure />} />
            <Route path="/companies" element={<CompanyProfiles />} />
            <Route path="/credit" element={<CreditStressTest />} />
            <Route path="/insurance" element={<InsuranceAccumulation />} />
            <Route path="/provenance" element={<ModelProvenance />} />
          </Routes>
          <footer className="mt-10 border-t border-line pt-4 text-xs leading-relaxed text-muted">
            <strong className="font-semibold text-ink">Research prototype.</strong> Environmental
            observations are real and sourced (NASA FIRMS via EOSDIS GIBS, Open-Meteo / ERA5); all
            companies, financial statements, bank exposures and insurance policies are entirely
            synthetic and fictional. Hazard scores are illustrative baselines - not calibrated
            probabilities, not validated forecasts, and not probabilities of default. This is not a
            production credit-rating or insurance-pricing system.
          </footer>
        </main>
      </div>
    </div>
  );
}
