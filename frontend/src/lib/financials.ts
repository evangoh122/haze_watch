/**
 * Baseline credit metrics for synthetic companies.
 *
 * Every formula is exposed and reproduced in the UI calculation traces so that
 * results are auditable. All figures are synthetic and illustrative.
 */

import type { CreditMetrics, FinancialStatement, SyntheticCompany } from "./types";

/** Net debt = short-term debt + long-term debt - cash. */
export function netDebt(statement: FinancialStatement): number {
  return statement.shortTermDebt + statement.longTermDebt - statement.cash;
}

export function computeMetrics(statement: FinancialStatement): CreditMetrics {
  const netDebtUsdM = netDebt(statement);

  // Leverage is not meaningful when EBITDA <= 0.
  const netDebtToEbitda =
    statement.ebitda > 0 ? netDebtUsdM / statement.ebitda : null;

  // Interest coverage is not meaningful when interest expense <= 0.
  const interestCoverage =
    statement.interestExpense > 0
      ? statement.ebitda / statement.interestExpense
      : null;

  const currentRatio =
    statement.currentLiabilities > 0
      ? statement.currentAssets / statement.currentLiabilities
      : Number.POSITIVE_INFINITY;

  // Liquidity runway: months of negative operating cash flow covered by cash.
  // Null when operating cash flow is positive (no burn to cover).
  const liquidityRunwayMonths =
    statement.operatingCashFlow < 0
      ? statement.cash / (-statement.operatingCashFlow / 12)
      : null;

  return {
    ebitdaUsdM: statement.ebitda,
    netDebtUsdM,
    netDebtToEbitda,
    interestCoverage,
    currentRatio,
    liquidityRunwayMonths,
    operatingCashFlowUsdM: statement.operatingCashFlow,
    cashUsdM: statement.cash,
  };
}

export function latestStatement(company: SyntheticCompany): FinancialStatement {
  return company.statements[company.statements.length - 1];
}

export interface StatementChecks {
  balanceSheetOk: boolean;
  ebitdaOk: boolean;
}

/** Accounting identities used in the data-quality tests and UI badges. */
export function checkStatement(statement: FinancialStatement): StatementChecks {
  const eq = 1e-6;
  return {
    balanceSheetOk:
      Math.abs(
        statement.totalAssets -
          (statement.totalLiabilities + statement.totalEquity),
      ) < eq,
    ebitdaOk:
      Math.abs(statement.ebitda - (statement.revenue - statement.cashOpex)) < eq,
  };
}
