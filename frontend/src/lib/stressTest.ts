/**
 * Auditable credit stress-scenario engine (synthetic data only).
 *
 * Model - a 12-month scenario year (every formula is echoed in the trace):
 *   f              = min(1, recoveryMonths / 12)         disrupted share of the year
 *   affectedRev    = revenue * landAffectedPct / 100
 *   productionLoss = affectedRev * productionDisruptionPct / 100
 *   marketLoss     = (revenue - productionLoss) * revenueReductionPct / 100
 *                    (applied to remaining revenue to avoid double counting)
 *   revenueLost    = min(revenue, productionLoss + marketLoss) * f
 *   opexIncrease   = cashOpex * opexIncreasePct / 100 * f
 *   remediation    = remediationCostUsdM                  (one-off in the year)
 *   ebitdaStressed = ebitda - revenueLost - opexIncrease - remediation
 *   wcDraw         = revenue * workingCapitalPct / 100 * f
 *   ocfStressed    = ocf + (ebitdaStressed - ebitda) - wcDraw
 *   netDebtStressed= netDebt - (ocfStressed - ocf)
 *                    (delta-based: only the scenario's cash-flow effect moves
 *                     debt; a zero-assumption scenario leaves metrics unchanged)
 *
 * Illustrative monitoring thresholds - NOT any institution's policy.
 */

import { computeMetrics, latestStatement, netDebt } from "./financials";
import type {
  CreditMetrics,
  FinancialStatement,
  MonitoringStatus,
  SyntheticCompany,
  TraceStep,
} from "./types";

export interface ScenarioAssumptions {
  landAffectedPct: number;
  productionDisruptionPct: number;
  revenueReductionPct: number;
  opexIncreasePct: number;
  recoveryMonths: number;
  remediationCostUsdM: number;
  workingCapitalPct: number;
}

export interface StressImpacts {
  revenueLostUsdM: number;
  opexIncreaseUsdM: number;
  remediationUsdM: number;
  workingCapitalDrawUsdM: number;
  ebitdaDeltaUsdM: number;
  ocfDeltaUsdM: number;
}

export interface StressResult {
  baselineMetrics: CreditMetrics;
  stressedMetrics: CreditMetrics;
  impacts: StressImpacts;
  monitoringStatus: MonitoringStatus;
  warnings: string[];
  trace: TraceStep[];
}

/** Illustrative thresholds used for monitoring status (documented, user-visible). */
export const THRESHOLDS = {
  covenantLeverageX: 5.0,
  covenantCoverageX: 1.5,
  watchLeverageX: 3.5,
  watchCoverageX: 2.5,
} as const;

export const DEFAULT_ASSUMPTIONS: ScenarioAssumptions = {
  landAffectedPct: 20,
  productionDisruptionPct: 40,
  revenueReductionPct: 5,
  opexIncreasePct: 10,
  recoveryMonths: 6,
  remediationCostUsdM: 8,
  workingCapitalPct: 5,
};

export function runStressScenario(
  company: SyntheticCompany,
  assumptions: ScenarioAssumptions,
): StressResult {
  const statement: FinancialStatement = latestStatement(company);
  const trace: TraceStep[] = [];
  const warnings: string[] = [];

  const step = (label: string, formula: string, value: number, unit: string): number => {
    trace.push({ label, formula, value, unit });
    return value;
  };

  const f = step(
    "Disrupted share of scenario year",
    "min(1, recoveryMonths / 12)",
    Math.min(1, assumptions.recoveryMonths / 12),
    "share",
  );

  const affectedRev = step(
    "Revenue tied to affected land",
    "revenue * landAffectedPct / 100",
    (statement.revenue * assumptions.landAffectedPct) / 100,
    "USD m",
  );
  const productionLoss = step(
    "Production disruption loss",
    "affectedRevenue * productionDisruptionPct / 100",
    (affectedRev * assumptions.productionDisruptionPct) / 100,
    "USD m",
  );
  const marketLoss = step(
    "Additional revenue reduction",
    "(revenue - productionLoss) * revenueReductionPct / 100",
    ((statement.revenue - productionLoss) * assumptions.revenueReductionPct) / 100,
    "USD m",
  );
  const revenueLost = step(
    "Revenue lost in scenario year",
    "min(revenue, productionLoss + marketLoss) * f",
    Math.min(statement.revenue, productionLoss + marketLoss) * f,
    "USD m",
  );
  const opexIncrease = step(
    "Operating cost increase",
    "cashOpex * opexIncreasePct / 100 * f",
    (statement.cashOpex * assumptions.opexIncreasePct * f) / 100,
    "USD m",
  );
  const remediation = step(
    "Remediation cost (one-off)",
    "remediationCostUsdM",
    assumptions.remediationCostUsdM,
    "USD m",
  );
  const ebitdaStressed = step(
    "Stressed EBITDA",
    "ebitda - revenueLost - opexIncrease - remediation",
    statement.ebitda - revenueLost - opexIncrease - remediation,
    "USD m",
  );
  const wcDraw = step(
    "Working capital draw",
    "revenue * workingCapitalPct / 100 * f",
    (statement.revenue * assumptions.workingCapitalPct * f) / 100,
    "USD m",
  );
  const ocfStressed = step(
    "Stressed operating cash flow",
    "ocf + (ebitdaStressed - ebitda) - workingCapitalDraw",
    statement.operatingCashFlow + (ebitdaStressed - statement.ebitda) - wcDraw,
    "USD m",
  );
  const netDebtStressed = step(
    "Stressed net debt",
    "netDebt - (ocfStressed - ocf)",
    netDebt(statement) - (ocfStressed - statement.operatingCashFlow),
    "USD m",
  );

  const baselineMetrics = computeMetrics(statement);
  const stressedMetrics: CreditMetrics = {
    ebitdaUsdM: ebitdaStressed,
    netDebtUsdM: netDebtStressed,
    netDebtToEbitda: ebitdaStressed > 0 ? netDebtStressed / ebitdaStressed : null,
    interestCoverage:
      statement.interestExpense > 0 ? ebitdaStressed / statement.interestExpense : null,
    currentRatio:
      statement.currentLiabilities > 0
        ? (statement.currentAssets - wcDraw) / statement.currentLiabilities
        : Number.POSITIVE_INFINITY,
    liquidityRunwayMonths:
      ocfStressed < 0 ? statement.cash / (-ocfStressed / 12) : null,
    operatingCashFlowUsdM: ocfStressed,
    cashUsdM: statement.cash,
  };

  // Monitoring status from ILLUSTRATIVE thresholds (not any institution's policy).
  const leverage = stressedMetrics.netDebtToEbitda;
  const coverage = stressedMetrics.interestCoverage;
  let monitoringStatus: MonitoringStatus = "Within watch thresholds";
  if (
    (leverage !== null && leverage > THRESHOLDS.covenantLeverageX) ||
    (coverage !== null && coverage < THRESHOLDS.covenantCoverageX)
  ) {
    monitoringStatus = "Covenant pressure";
  } else if (
    (leverage !== null && leverage > THRESHOLDS.watchLeverageX) ||
    (coverage !== null && coverage < THRESHOLDS.watchCoverageX) ||
    stressedMetrics.currentRatio < 1
  ) {
    monitoringStatus = "Enhanced monitoring";
  }

  if (ebitdaStressed <= 0) warnings.push("Stressed EBITDA is non-positive: leverage ratios are not meaningful.");
  if (assumptions.recoveryMonths > 12) {
    warnings.push("Recovery extends beyond the 12-month scenario horizon; multi-year impacts are not modeled.");
  }
  if (ocfStressed < 0) warnings.push("Stressed operating cash flow is negative: liquidity runway applies.");

  const impacts: StressImpacts = {
    revenueLostUsdM: revenueLost,
    opexIncreaseUsdM: opexIncrease,
    remediationUsdM: remediation,
    workingCapitalDrawUsdM: wcDraw,
    ebitdaDeltaUsdM: ebitdaStressed - statement.ebitda,
    ocfDeltaUsdM: ocfStressed - statement.operatingCashFlow,
  };

  return {
    baselineMetrics,
    stressedMetrics,
    impacts,
    monitoringStatus,
    warnings,
    trace,
  };
}
