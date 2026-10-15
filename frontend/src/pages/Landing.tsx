import { Link } from "react-router-dom";
import ScqaNarrative from "../components/scqa/ScqaNarrative";
import SyntheticDataBadge from "../components/common/SyntheticDataBadge";

const CAPABILITIES = [
  {
    title: "Geospatial exposure over real observations",
    body: "NASA FIRMS hotspots and Open-Meteo weather joined to concession polygons with audited, leakage-safe pipelines.",
    status: "Implemented",
  },
  {
    title: "Synthetic credit stress testing",
    body: "Auditable scenario engine: every ratio is traceable to a documented formula and assumption.",
    status: "Implemented",
  },
  {
    title: "Grounded analyst chat",
    body: "Answers cite registered datasets and distinguish observed, derived and synthetic figures.",
    status: "Implemented",
  },
  {
    title: "Fire escalation forecasting",
    body: "XGBoost 24-72h forecasts with spatial backtesting and calibration, beating persistence baselines.",
    status: "Planned (Phase 2)",
  },
  {
    title: "Burned-area segmentation",
    body: "U-Net / SegFormer on multispectral imagery, evaluated against NDVI/NBR baselines.",
    status: "Planned (Phase 3)",
  },
  {
    title: "Insurance accumulation",
    body: "Portfolio accumulation and scenario losses with documented deductible/limit ordering.",
    status: "Planned (Phase 4)",
  },
];

export default function Landing() {
  return (
    <div className="space-y-10">
      <section className="rounded-xl bg-slate-900 px-8 py-10 text-white">
        <p className="text-xs font-medium uppercase tracking-widest text-muted">
          Research prototype - independent project
        </p>
        <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight">
          Geospatial climate risk intelligence for banks and insurers
        </h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Translate real wildfire and haze activity in Indonesia into illustrative credit and
          insurance risk indicators - with real environmental observations paired with entirely
          synthetic companies, financial statements and exposures.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/banking"
            className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-500"
          >
            Run the banking demo
          </Link>
          <Link
            to="/chat"
            className="rounded-md border border-slate-600 px-5 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            Ask the data
          </Link>
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-primary">The business case</h2>
          <SyntheticDataBadge compact />
        </div>
        <ScqaNarrative
          block={{
            situation:
              "Banks and insurers in Southeast Asia hold portfolios of plantation, forestry and agricultural borrowers whose assets are physically exposed to recurring wildfire and haze episodes. Satellite observation of these hazards is public, timely and objective.",
            complication:
              "The link from environmental hazard to financial impact is not made systematically: exposure is discovered late, geospatial data is hard to join to credit files, and scenario analysis rarely reaches borrower cash flow. Regulatory expectations for climate risk management are rising while tooling stays manual.",
            question:
              "How can an institution turn real fire observations into a measurable, auditable view of which borrowers are exposed, what a plausible disruption does to debt-servicing capacity, and where portfolio concentration creates early-warning needs?",
            answer:
              "A geospatial risk layer that joins observed hazards to asset locations, runs transparent financial stress scenarios on borrower-level statements, and shows every calculation with its provenance. This prototype demonstrates that pipeline end to end - with real environmental data and fully synthetic commercial data - to make the approach inspectable before any production commitment.",
          }}
        />
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-primary">What it does</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {CAPABILITIES.map((capability) => (
            <div key={capability.title} className="rounded-lg border border-border bg-surface-elevated p-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-primary">{capability.title}</h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    capability.status === "Implemented"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-slate-100 text-muted"
                  }`}
                >
                  {capability.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-secondary">{capability.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
        <strong>Important.</strong> Environmental observations are real and sourced (NASA FIRMS,
        Open-Meteo / ERA5). All companies, financial statements, bank exposures and insurance
        policies are entirely synthetic and fictional. Hazard scores are illustrative baselines -
        not calibrated probabilities, not validated forecasts, and not probabilities of default.
        This is a research prototype, not a production credit-rating or insurance-pricing system.
      </section>
    </div>
  );
}
