import { describe, expect, it } from "vitest";

import { getCompany } from "../data/syntheticCompanies";
import { computeMetrics, latestStatement } from "./financials";
import {
  DEFAULT_ASSUMPTIONS,
  runStressScenario,
  type ScenarioAssumptions,
} from "./stressTest";

const ZERO: ScenarioAssumptions = {
  landAffectedPct: 0,
  productionDisruptionPct: 0,
  revenueReductionPct: 0,
  opexIncreasePct: 0,
  recoveryMonths: 12,
  remediationCostUsdM: 0,
  workingCapitalPct: 0,
};

describe("stressTest engine", () => {
  it("a zero-assumption scenario changes nothing", () => {
    const company = getCompany("SYN-001");
    const result = runStressScenario(company, ZERO);
    const baseline = computeMetrics(latestStatement(company));

    expect(result.impacts.ebitdaDeltaUsdM).toBe(0);
    expect(result.impacts.revenueLostUsdM).toBe(0);
    expect(result.stressedMetrics.ebitdaUsdM).toBeCloseTo(baseline.ebitdaUsdM, 6);
    expect(result.stressedMetrics.netDebtToEbitda).toBeCloseTo(baseline.netDebtToEbitda ?? 0, 6);
  });

  it("every EBITDA impact is explained by the documented formulas", () => {
    const company = getCompany("SYN-001");
    const result = runStressScenario(company, DEFAULT_ASSUMPTIONS);
    const statement = latestStatement(company);
    const { revenueLostUsdM, opexIncreaseUsdM, remediationUsdM } = result.impacts;

    expect(result.stressedMetrics.ebitdaUsdM).toBeCloseTo(
      statement.ebitda - revenueLostUsdM - opexIncreaseUsdM - remediationUsdM,
      6,
    );
  });

  it("revenue loss is capped at total revenue (no double counting)", () => {
    const company = getCompany("SYN-003");
    const extreme: ScenarioAssumptions = {
      ...ZERO,
      landAffectedPct: 100,
      productionDisruptionPct: 100,
      revenueReductionPct: 50,
    };
    const result = runStressScenario(company, extreme);
    expect(result.impacts.revenueLostUsdM).toBeLessThanOrEqual(
      latestStatement(company).revenue + 1e-9,
    );
  });

  it("flags the leveraged borrower as worse off than the cash-rich one", () => {
    const severe: ScenarioAssumptions = {
      landAffectedPct: 60,
      productionDisruptionPct: 80,
      revenueReductionPct: 10,
      opexIncreasePct: 15,
      recoveryMonths: 9,
      remediationCostUsdM: 20,
      workingCapitalPct: 10,
    };
    const stressed = runStressScenario(getCompany("SYN-001"), severe);
    const resilient = runStressScenario(getCompany("SYN-002"), severe);

    const rank: Record<string, number> = {
      "Within watch thresholds": 0,
      "Enhanced monitoring": 1,
      "Covenant pressure": 2,
    };
    expect(["Covenant pressure", "Enhanced monitoring"]).toContain(stressed.monitoringStatus);
    expect(rank[stressed.monitoringStatus]).toBeGreaterThanOrEqual(
      rank[resilient.monitoringStatus],
    );
    // Relative EBITDA damage is larger for the leveraged borrower.
    const stressRatio = stressed.stressedMetrics.ebitdaUsdM / stressed.baselineMetrics.ebitdaUsdM;
    const resilienceRatio =
      resilient.stressedMetrics.ebitdaUsdM / resilient.baselineMetrics.ebitdaUsdM;
    expect(stressRatio).toBeLessThan(resilienceRatio);
  });

  it("emits a complete, finite calculation trace", () => {
    const result = runStressScenario(getCompany("SYN-001"), DEFAULT_ASSUMPTIONS);
    expect(result.trace.length).toBeGreaterThanOrEqual(10);
    for (const step of result.trace) {
      expect(step.formula.length).toBeGreaterThan(0);
      expect(Number.isFinite(step.value)).toBe(true);
    }
  });

  it("warns when recovery exceeds the scenario horizon", () => {
    const result = runStressScenario(getCompany("SYN-001"), {
      ...DEFAULT_ASSUMPTIONS,
      recoveryMonths: 18,
    });
    expect(result.warnings.some((w) => w.includes("multi-year"))).toBe(true);
  });

  it("warns and reports n.m. leverage when stressed EBITDA turns negative", () => {
    const result = runStressScenario(getCompany("SYN-003"), {
      ...DEFAULT_ASSUMPTIONS,
      landAffectedPct: 100,
      productionDisruptionPct: 100,
      remediationCostUsdM: 30,
    });
    expect(result.stressedMetrics.ebitdaUsdM).toBeLessThan(0);
    expect(result.stressedMetrics.netDebtToEbitda).toBeNull();
    expect(result.warnings.some((w) => w.includes("non-positive"))).toBe(true);
  });
});
