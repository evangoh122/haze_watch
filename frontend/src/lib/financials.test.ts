import { describe, expect, it } from "vitest";

import { checkStatement, computeMetrics, netDebt } from "./financials";
import type { FinancialStatement } from "./types";

const statement: FinancialStatement = {
  period: "2025",
  revenue: 341,
  cashOpex: 281,
  ebitda: 60,
  interestExpense: 37,
  capex: 18,
  operatingCashFlow: 17,
  cash: 19,
  shortTermDebt: 78,
  longTermDebt: 232,
  currentAssets: 126,
  currentLiabilities: 131,
  totalAssets: 630,
  totalLiabilities: 431,
  totalEquity: 199,
};

describe("financials", () => {
  it("computes net debt as debt minus cash", () => {
    expect(netDebt(statement)).toBe(78 + 232 - 19);
  });

  it("computes credit metrics from the statement", () => {
    const metrics = computeMetrics(statement);
    expect(metrics.netDebtUsdM).toBe(291);
    expect(metrics.netDebtToEbitda).toBeCloseTo(291 / 60, 6);
    expect(metrics.interestCoverage).toBeCloseTo(60 / 37, 6);
    expect(metrics.currentRatio).toBeCloseTo(126 / 131, 6);
    // Positive operating cash flow: no burn to cover.
    expect(metrics.liquidityRunwayMonths).toBeNull();
  });

  it("returns null ratios instead of dividing by zero", () => {
    const broken = { ...statement, ebitda: -5, interestExpense: 0 };
    const metrics = computeMetrics(broken);
    expect(metrics.netDebtToEbitda).toBeNull();
    expect(metrics.interestCoverage).toBeNull();
  });

  it("verifies the accounting identities of a statement", () => {
    const checks = checkStatement(statement);
    expect(checks.balanceSheetOk).toBe(true);
    expect(checks.ebitdaOk).toBe(true);

    const unbalanced = { ...statement, totalEquity: 200 };
    expect(checkStatement(unbalanced).balanceSheetOk).toBe(false);
  });

  it("computes liquidity runway when operating cash flow is negative", () => {
    const burning = { ...statement, operatingCashFlow: -24 };
    const metrics = computeMetrics(burning);
    // 19 cash / (24 burn per year / 12) = 9.5 months
    expect(metrics.liquidityRunwayMonths).toBeCloseTo(9.5, 6);
  });
});
