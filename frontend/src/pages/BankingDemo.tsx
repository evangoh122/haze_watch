import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import CalculationTrace from "../components/common/CalculationTrace";
import KpiCard from "../components/common/KpiCard";
import SyntheticDataBadge from "../components/common/SyntheticDataBadge";
import ComparisonChart from "../components/charts/ComparisonChart";
import ScenarioSlider from "../components/scenario/ScenarioSlider";
import { SYNTHETIC_COMPANIES, SYNTHETIC_NOTICE, getCompany } from "../data/syntheticCompanies";
import { computeMetrics, latestStatement } from "../lib/financials";
import { fmtRatio, fmtUsdM } from "../lib/format";
import {
  DEFAULT_ASSUMPTIONS,
  runStressScenario,
  type ScenarioAssumptions,
} from "../lib/stressTest";

/**
 * Working banking demo (vertical slice): select a fictional borrower, adjust
 * fire-disruption assumptions, and inspect an auditable stress assessment.
 */
export default function BankingDemo() {
  const [companyId, setCompanyId] = useState(SYNTHETIC_COMPANIES[0].companyId);
  const [assumptions, setAssumptions] = useState<ScenarioAssumptions>(DEFAULT_ASSUMPTIONS);

  const company = getCompany(companyId);
  const statement = latestStatement(company);
  const baseline = useMemo(() => computeMetrics(statement), [statement]);
  const result = useMemo(() => runStressScenario(company, assumptions), [company, assumptions]);

  const set = (key: keyof ScenarioAssumptions) => (value: number) =>
    setAssumptions((prev) => ({ ...prev, [key]: value }));

  const statusTone =
    result.monitoringStatus === "Covenant pressure"
      ? "alert"
      : result.monitoringStatus === "Enhanced monitoring"
        ? "warn"
        : "ok";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-primary">Credit stress testing</h1>
          <p className="text-sm text-secondary">
            Fire-disruption scenario on a fictional borrower - every output is traceable.
          </p>
        </div>
        <SyntheticDataBadge />
      </div>
      <p className="rounded-md border border-violet-200 bg-violet-50 px-4 py-2 text-xs text-violet-800">
        {SYNTHETIC_NOTICE}
      </p>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-1">
          <label className="block">
            <span className="text-sm font-medium text-secondary">Borrower (fictional)</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={companyId}
              onChange={(event) => setCompanyId(event.target.value)}
              aria-label="Borrower (fictional)"
            >
              {SYNTHETIC_COMPANIES.map((c) => (
                <option key={c.companyId} value={c.companyId}>
                  {c.fictionalName} - {c.archetype}
                </option>
              ))}
            </select>
          </label>

          <div className="rounded-lg border border-border bg-surface-elevated p-4 text-sm text-secondary">
            <p>{company.narrative}</p>
            <p className="mt-2 text-xs text-muted">
              {company.industry} - {company.assets.length} assets - facilities{" "}
              {company.facilities.map((f) => f.facilityType).join(", ")}
            </p>
          </div>

          <div className="space-y-4 rounded-lg border border-border bg-surface-elevated p-4">
            <h2 className="text-sm font-semibold text-primary">Scenario assumptions</h2>
            <ScenarioSlider label="Productive land affected" value={assumptions.landAffectedPct} min={0} max={100} step={1} unit="%" onChange={set("landAffectedPct")} />
            <ScenarioSlider label="Production disruption" value={assumptions.productionDisruptionPct} min={0} max={100} step={1} unit="%" onChange={set("productionDisruptionPct")} />
            <ScenarioSlider label="Additional revenue reduction" value={assumptions.revenueReductionPct} min={0} max={50} step={1} unit="%" onChange={set("revenueReductionPct")} hint="Applied to revenue remaining after production loss (no double counting)." />
            <ScenarioSlider label="Operating cost increase" value={assumptions.opexIncreasePct} min={0} max={50} step={1} unit="%" onChange={set("opexIncreasePct")} />
            <ScenarioSlider label="Recovery duration" value={assumptions.recoveryMonths} min={1} max={24} step={1} unit=" mo" onChange={set("recoveryMonths")} hint="Scales the disrupted share of the 12-month scenario year." />
            <ScenarioSlider label="Remediation cost" value={assumptions.remediationCostUsdM} min={0} max={50} step={1} unit="m" onChange={set("remediationCostUsdM")} />
            <ScenarioSlider label="Working capital impact" value={assumptions.workingCapitalPct} min={0} max={30} step={1} unit="%" onChange={set("workingCapitalPct")} />
          </div>
        </div>

        <div className="space-y-4 lg:col-span-2">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Net debt / EBITDA" value={fmtRatio(result.stressedMetrics.netDebtToEbitda)} sub={`baseline ${fmtRatio(baseline.netDebtToEbitda)}`} tone={statusTone} />
            <KpiCard label="EBITDA / interest" value={fmtRatio(result.stressedMetrics.interestCoverage)} sub={`baseline ${fmtRatio(baseline.interestCoverage)}`} tone={statusTone} />
            <KpiCard label="Stressed EBITDA" value={fmtUsdM(result.stressedMetrics.ebitdaUsdM)} sub={`baseline ${fmtUsdM(baseline.ebitdaUsdM)}`} />
            <KpiCard label="Monitoring status" value={result.monitoringStatus} sub="Illustrative thresholds" tone={statusTone} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <ComparisonChart
              title="Scenario impact (USD m)"
              unit="m"
              data={[
                { label: "EBITDA", baseline: baseline.ebitdaUsdM, stressed: result.stressedMetrics.ebitdaUsdM },
                { label: "Op. cash flow", baseline: baseline.operatingCashFlowUsdM, stressed: result.stressedMetrics.operatingCashFlowUsdM },
                { label: "Net debt", baseline: baseline.netDebtUsdM, stressed: result.stressedMetrics.netDebtUsdM },
              ]}
            />
            <ComparisonChart
              title="Credit ratios (x)"
              unit="x"
              data={[
                // Non-meaningful ratios stay null (chart gap), never plotted as 0.
                { label: "Net debt/EBITDA", baseline: baseline.netDebtToEbitda, stressed: result.stressedMetrics.netDebtToEbitda },
                { label: "EBITDA/interest", baseline: baseline.interestCoverage, stressed: result.stressedMetrics.interestCoverage },
                { label: "Current ratio", baseline: baseline.currentRatio, stressed: result.stressedMetrics.currentRatio },
              ]}
            />
          </div>

          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <strong>Warnings:</strong>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <CalculationTrace trace={result.trace} />

          <p className="text-xs text-muted">
            Scenario outputs are hypothetical illustrations computed from synthetic statements.
            Monitoring thresholds are illustrative and not any institution's policy. Hazard scores
            are not validated probabilities of default. See the{" "}
            <Link className="text-accent underline" to="/provenance">
              governance notes
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
