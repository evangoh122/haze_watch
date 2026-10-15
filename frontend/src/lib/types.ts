/**
 * Shared domain types for the SCQA website and risk demos.
 *
 * All company, financial, lending and insurance data in this application is
 * FICTIONAL and generated for demonstration. Environmental observations are real
 * and sourced (NASA EOSDIS GIBS / FIRMS, Open-Meteo) with attribution displayed
 * in the UI.
 */

export type DataType = "observed" | "derived" | "synthetic" | "illustrative";

export type Industry =
  | "Palm oil"
  | "Pulp & paper"
  | "Agriculture"
  | "Forestry"
  | "Industrial";

export type Archetype =
  | "Highly leveraged producer"
  | "Cash-rich diversified operator"
  | "Geographically concentrated borrower"
  | "Integrated operator, moderate leverage";

/** Annual synthetic financial statement, USD millions. */
export interface FinancialStatement {
  period: string;
  revenue: number;
  cashOpex: number;
  /** Defined as revenue - cashOpex. */
  ebitda: number;
  interestExpense: number;
  capex: number;
  operatingCashFlow: number;
  cash: number;
  shortTermDebt: number;
  longTermDebt: number;
  currentAssets: number;
  currentLiabilities: number;
  totalAssets: number;
  totalLiabilities: number;
  totalEquity: number;
}

export interface CompanyAsset {
  assetId: string;
  name: string;
  province: string;
  latitude: number;
  longitude: number;
  areaHa: number;
  /** Share of company productive land this asset represents (0..1). */
  productiveShare: number;
}

export interface BankFacility {
  facilityId: string;
  facilityType: string;
  limitUsdM: number;
  eadUsdM: number;
  maturityYear: number;
}

export interface SyntheticCompany {
  companyId: string;
  fictionalName: string;
  industry: Industry;
  archetype: Archetype;
  narrative: string;
  /** Oldest period first. */
  statements: FinancialStatement[];
  assets: CompanyAsset[];
  facilities: BankFacility[];
}

export interface InsurancePolicy {
  policyId: string;
  /** Fictional policyholder. */
  policyholder: string;
  companyId: string;
  assetId: string;
  region: string;
  coverageType: string;
  tivUsdM: number;
  limitUsdM: number;
  deductibleUsdM: number;
  inception: string;
  expiry: string;
}

/** Real point observation grid used for weather (Open-Meteo / ERA5). */
export interface WeatherStation {
  stationId: string;
  label: string;
  latitude: number;
  longitude: number;
}

export interface WeatherSnapshot {
  latitude: number;
  longitude: number;
  current: {
    time: string;
    temperature_2m: number;
    relative_humidity_2m: number;
    wind_speed_10m: number;
    precipitation: number;
  };
  daily: {
    time: string[];
    temperature_2m_max: number[];
    precipitation_sum: number[];
    relative_humidity_2m_mean: number[];
    wind_speed_10m_max: number[];
  };
}

export interface CreditMetrics {
  ebitdaUsdM: number;
  netDebtUsdM: number;
  netDebtToEbitda: number | null;
  interestCoverage: number | null;
  currentRatio: number;
  liquidityRunwayMonths: number | null;
  operatingCashFlowUsdM: number;
  cashUsdM: number;
}

export interface TraceStep {
  label: string;
  formula: string;
  value: number;
  unit: string;
}

export type MonitoringStatus =
  | "Within watch thresholds"
  | "Enhanced monitoring"
  | "Covenant pressure";
