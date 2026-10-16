/**
 * SYNTHETIC DEMONSTRATION DATA - entirely fictional.
 *
 * Companies, statements, assets, ownership and lending exposures here are
 * generated for demonstration. They do not describe any real company or any
 * real bank's customer. Statements satisfy:
 *   totalAssets = totalLiabilities + totalEquity
 *   ebitda = revenue - cashOpex
 */

import type { SyntheticCompany } from "../lib/types";

export const SYNTHETIC_NOTICE =
  "All companies and financial figures on this page are entirely synthetic and fictional.";

export const SYNTHETIC_COMPANIES: SyntheticCompany[] = [
  {
    companyId: "SYN-001",
    fictionalName: "Nusantara Sawit Merdeka (fictional)",
    industry: "Palm oil",
    archetype: "Highly leveraged producer",
    narrative:
      "Fictional mid-size palm oil producer with rising leverage and thin interest cover. Used to demonstrate early-warning behavior under a fire-disruption scenario.",
    statements: [
      { period: "FY2023", revenue: 385, cashOpex: 293, ebitda: 92, interestExpense: 31, capex: 25, operatingCashFlow: 48, cash: 34, shortTermDebt: 60, longTermDebt: 230, currentAssets: 138, currentLiabilities: 118, totalAssets: 665, totalLiabilities: 415, totalEquity: 250 },
      { period: "FY2024", revenue: 362, cashOpex: 289, ebitda: 73, interestExpense: 35, capex: 21, operatingCashFlow: 29, cash: 26, shortTermDebt: 72, longTermDebt: 235, currentAssets: 132, currentLiabilities: 126, totalAssets: 648, totalLiabilities: 428, totalEquity: 220 },
      { period: "FY2025", revenue: 341, cashOpex: 281, ebitda: 60, interestExpense: 37, capex: 18, operatingCashFlow: 17, cash: 19, shortTermDebt: 78, longTermDebt: 232, currentAssets: 126, currentLiabilities: 131, totalAssets: 630, totalLiabilities: 431, totalEquity: 199 },
    ],
    assets: [
      { assetId: "A-101", name: "Kalteng Estate (fictional)", province: "Central Kalimantan", latitude: -2.21, longitude: 113.92, areaHa: 16800, productiveShare: 0.62 },
      { assetId: "A-102", name: "Seruyan Mill Estate (fictional)", province: "Central Kalimantan", latitude: -2.55, longitude: 113.4, areaHa: 9400, productiveShare: 0.55 },
    ],
    facilities: [
      { facilityId: "F-1", facilityType: "Term loan", limitUsdM: 180, eadUsdM: 162, maturityYear: 2029 },
      { facilityId: "F-2", facilityType: "Revolving credit", limitUsdM: 60, eadUsdM: 48, maturityYear: 2027 },
    ],
  },
  {
    companyId: "SYN-002",
    fictionalName: "Borneo Lestari Agri (fictional)",
    industry: "Palm oil",
    archetype: "Cash-rich diversified operator",
    narrative:
      "Fictional diversified operator with strong liquidity and low leverage. Used to demonstrate resilience of well-capped borrowers to the same hazard scenario.",
    statements: [
      { period: "FY2023", revenue: 512, cashOpex: 384, ebitda: 128, interestExpense: 21, capex: 40, operatingCashFlow: 96, cash: 142, shortTermDebt: 48, longTermDebt: 180, currentAssets: 240, currentLiabilities: 130, totalAssets: 980, totalLiabilities: 358, totalEquity: 622 },
      { period: "FY2024", revenue: 545, cashOpex: 402, ebitda: 143, interestExpense: 22, capex: 44, operatingCashFlow: 110, cash: 171, shortTermDebt: 45, longTermDebt: 172, currentAssets: 258, currentLiabilities: 138, totalAssets: 1042, totalLiabilities: 355, totalEquity: 687 },
      { period: "FY2025", revenue: 571, cashOpex: 419, ebitda: 152, interestExpense: 23, capex: 47, operatingCashFlow: 121, cash: 202, shortTermDebt: 42, longTermDebt: 165, currentAssets: 276, currentLiabilities: 144, totalAssets: 1105, totalLiabilities: 351, totalEquity: 754 },
    ],
    assets: [
      { assetId: "A-201", name: "Kalbar Estate (fictional)", province: "West Kalimantan", latitude: 0.53, longitude: 109.52, areaHa: 22100, productiveShare: 0.71 },
      { assetId: "A-202", name: "Ketapang Estate (fictional)", province: "West Kalimantan", latitude: 0.2, longitude: 110.1, areaHa: 12600, productiveShare: 0.64 },
    ],
    facilities: [
      { facilityId: "F-3", facilityType: "Term loan", limitUsdM: 150, eadUsdM: 121, maturityYear: 2030 },
    ],
  },
  {
    companyId: "SYN-003",
    fictionalName: "Sumatra Palm Ventures (fictional)",
    industry: "Agriculture",
    archetype: "Geographically concentrated borrower",
    narrative:
      "Fictional borrower with most assets in one province - demonstrates geographic concentration risk in portfolio surveillance.",
    statements: [
      { period: "FY2023", revenue: 268, cashOpex: 206, ebitda: 62, interestExpense: 18, capex: 14, operatingCashFlow: 33, cash: 22, shortTermDebt: 38, longTermDebt: 118, currentAssets: 92, currentLiabilities: 76, totalAssets: 402, totalLiabilities: 214, totalEquity: 188 },
      { period: "FY2024", revenue: 259, cashOpex: 205, ebitda: 54, interestExpense: 19, capex: 12, operatingCashFlow: 24, cash: 18, shortTermDebt: 44, longTermDebt: 121, currentAssets: 88, currentLiabilities: 80, totalAssets: 396, totalLiabilities: 222, totalEquity: 174 },
      { period: "FY2025", revenue: 247, cashOpex: 202, ebitda: 45, interestExpense: 20, capex: 10, operatingCashFlow: 14, cash: 13, shortTermDebt: 49, longTermDebt: 122, currentAssets: 84, currentLiabilities: 83, totalAssets: 390, totalLiabilities: 229, totalEquity: 161 },
    ],
    assets: [
      { assetId: "A-301", name: "Jambi Estate (fictional)", province: "Jambi", latitude: -0.88, longitude: 104.51, areaHa: 11200, productiveShare: 0.48 },
      { assetId: "A-302", name: "Batin Estate (fictional)", province: "Jambi", latitude: -1.35, longitude: 104.2, areaHa: 8300, productiveShare: 0.41 },
    ],
    facilities: [
      { facilityId: "F-4", facilityType: "Term loan", limitUsdM: 95, eadUsdM: 84, maturityYear: 2028 },
      { facilityId: "F-5", facilityType: "Working capital line", limitUsdM: 25, eadUsdM: 19, maturityYear: 2027 },
    ],
  },
];

export function getCompany(companyId: string): SyntheticCompany {
  const company = SYNTHETIC_COMPANIES.find((c) => c.companyId === companyId);
  if (!company) throw new Error(`unknown synthetic company: ${companyId}`);
  return company;
}
