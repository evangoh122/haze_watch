/** Display formatting helpers. Values are USD millions unless stated. */

export function fmtUsdM(value: number, digits = 1): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}$${Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}m`;
}

export function fmtRatio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "n.m.";
  return `${value.toFixed(1)}x`;
}

export function fmtMonths(value: number | null): string {
  if (value === null) return "n/a (positive OCF)";
  if (!Number.isFinite(value)) return "n.m.";
  return `${value.toFixed(1)} mo`;
}

export function fmtPct(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

export function fmtNumber(value: number, digits = 1): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtHa(value: number): string {
  return `${Math.round(value).toLocaleString("en-US")} ha`;
}
