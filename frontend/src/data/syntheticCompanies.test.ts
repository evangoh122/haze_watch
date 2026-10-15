import { describe, expect, it } from "vitest";

import { SYNTHETIC_COMPANIES } from "./syntheticCompanies";

describe("synthetic demonstration data", () => {
  it("every statement satisfies the accounting identities", () => {
    for (const company of SYNTHETIC_COMPANIES) {
      for (const statement of company.statements) {
        expect(
          statement.totalAssets,
          `${company.companyId} ${statement.period} balance sheet`,
        ).toBeCloseTo(statement.totalLiabilities + statement.totalEquity, 6);
        expect(
          statement.ebitda,
          `${company.companyId} ${statement.period} EBITDA`,
        ).toBeCloseTo(statement.revenue - statement.cashOpex, 6);
      }
    }
  });

  it("all demo objects are visibly fictional", () => {
    for (const company of SYNTHETIC_COMPANIES) {
      expect(company.fictionalName.toLowerCase()).toContain("fictional");
    }
  });

  it("assets carry plausible Indonesian coordinates", () => {
    for (const company of SYNTHETIC_COMPANIES) {
      for (const asset of company.assets) {
        expect(asset.latitude).toBeGreaterThan(-12);
        expect(asset.latitude).toBeLessThan(7);
        expect(asset.longitude).toBeGreaterThan(94);
        expect(asset.longitude).toBeLessThan(142);
      }
    }
  });
});
