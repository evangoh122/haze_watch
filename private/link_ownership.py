"""Private ownership + financial linkage for real listed companies. RESEARCH ONLY.

This module links real Indonesian concession boundaries (which carry a group name
with ``attribution_confidence = "unverified"``) to their listed parent companies,
and reads hand-entered financial statements sourced from public filings
(SGXNet / IDX / Bursa Malaysia annual reports).

GOVERNANCE (docs/governance.md; project_profile.md sections 3 and 10)
--------------------------------------------------------------------
- Never publish, screenshot or commit anything produced here. The YAML under
  ``private/companies/`` is gitignored on purpose.
- Every figure must carry a citation (``citations`` + ``source_ref``); entries
  without one are rejected by validation.
- Geographic overlap between a fire detection and a concession is NOT evidence
  of causation, culpability or responsibility and must never be presented as such.
- Attribution stays ``unverified`` until a filing (or RSPO/SPOTT/Trase) confirms
  the parent-subsidiary link.
- Outputs are internal research only: no named public claims.

Usage (hand-sourced workflow)::

    python private/link_ownership.py \
        --companies private/companies \
        --concessions data/processed/plantation_polygons.parquet
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

# Accounting identities are exact in principle; allow for filing rounding.
BALANCE_TOLERANCE_ABS = 1.0  # USD millions
BALANCE_TOLERANCE_REL = 0.005  # 0.5% of total assets

TEMPLATE_NAME = "_template.yaml"


class Citation(BaseModel):
    """Where a figure came from, so it can be re-checked years later."""

    url: str
    page: str | None = None
    retrieved_on: date
    note: str | None = None


class Parent(BaseModel):
    name: str
    ticker: str
    exchange: str
    reporting_currency: str
    fiscal_year_end: str | None = None
    # GFW/BNPB ``group_attribution`` strings that map to this parent.
    aliases: list[str] = Field(default_factory=list)


class OwnershipLink(BaseModel):
    parent: str
    subsidiary: str
    stake_pct: float = Field(ge=0, le=100)
    as_of: str
    source_ref: str


class Statement(BaseModel):
    """One consolidated period, in the parent's reporting currency (millions)."""

    period: str
    revenue: float
    cash_opex: float
    ebitda: float
    interest_expense: float
    cash: float
    short_term_debt: float
    long_term_debt: float
    current_assets: float
    current_liabilities: float
    total_assets: float
    total_liabilities: float
    total_equity: float
    operating_cash_flow: float
    capex: float
    source_ref: str

    @model_validator(mode="after")
    def _identities(self) -> Statement:
        tol = max(
            BALANCE_TOLERANCE_ABS, BALANCE_TOLERANCE_REL * abs(self.total_assets)
        )
        bs = self.total_assets - (self.total_liabilities + self.total_equity)
        if abs(bs) > tol:
            raise ValueError(
                f"{self.period}: total_assets - (total_liabilities + total_equity) "
                f"= {bs:.3f} exceeds tolerance {tol:.3f}"
            )
        ebitda = self.ebitda - (self.revenue - self.cash_opex)
        if abs(ebitda) > tol:
            raise ValueError(
                f"{self.period}: ebitda - (revenue - cash_opex) = {ebitda:.3f} "
                f"exceeds tolerance {tol:.3f}"
            )
        return self


class Facility(BaseModel):
    facility: str
    ead: float
    maturity_year: int


class CompanyFile(BaseModel):
    parent: Parent
    ownership: list[OwnershipLink] = Field(default_factory=list)
    statements: list[Statement] = Field(min_length=1)
    facilities: list[Facility] = Field(default_factory=list)
    citations: dict[str, Citation]

    @model_validator(mode="after")
    def _references(self) -> CompanyFile:
        if not self.citations:
            raise ValueError("at least one citation is required")
        refs = set(self.citations)
        used = {o.source_ref for o in self.ownership} | {
            s.source_ref for s in self.statements
        }
        missing = sorted(used - refs)
        if missing:
            raise ValueError(
                f"source_ref {missing} not defined under citations "
                f"(known: {sorted(refs)})"
            )
        return self


# --- metrics (mirrors frontend/src/lib/financials.ts) -----------------------


def metrics(statement: Statement) -> dict[str, float | None]:
    """Credit metrics. ``None`` where a ratio is not meaningful (not zero)."""
    net_debt = statement.short_term_debt + statement.long_term_debt - statement.cash
    return {
        "net_debt": net_debt,
        "net_debt_to_ebitda": net_debt / statement.ebitda if statement.ebitda > 0 else None,
        "interest_coverage": (
            statement.ebitda / statement.interest_expense
            if statement.interest_expense > 0
            else None
        ),
        "current_ratio": (
            statement.current_assets / statement.current_liabilities
            if statement.current_liabilities > 0
            else float("inf")
        ),
        "liquidity_runway_months": (
            statement.cash / (-statement.operating_cash_flow / 12)
            if statement.operating_cash_flow < 0
            else None
        ),
        "cash": statement.cash,
        "ebitda": statement.ebitda,
    }


def latest_statement(company: CompanyFile) -> Statement:
    """Oldest-first convention: the last statement in the file is the newest."""
    return company.statements[-1]


# --- loading -----------------------------------------------------------------


def load_company_file(path: Path) -> CompanyFile:
    """Parse and validate one hand-sourced company file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"{path}: expected a YAML mapping at the top level")
    return CompanyFile(**raw)


def load_companies(directory: Path) -> dict[str, CompanyFile]:
    """Load every ``*.yaml`` except ``_``-prefixed templates. Keyed by ticker."""
    companies: dict[str, CompanyFile] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        company = load_company_file(path)
        companies[company.parent.ticker] = company
    return companies


# --- coverage ----------------------------------------------------------------


def alias_index(companies: dict[str, CompanyFile]) -> dict[str, str]:
    """casefolded alias/name -> ticker."""
    index: dict[str, str] = {}
    for ticker, company in companies.items():
        for alias in [company.parent.name, *company.parent.aliases]:
            index[alias.strip().casefold()] = ticker
    return index


def attribution_coverage(
    concessions: Any,
    companies: dict[str, CompanyFile],
    *,
    group_column: str = "group_attribution",
    top_unlinked: int = 20,
) -> dict[str, Any]:
    """How many concession polygons can be linked to a verified/target parent.

    Coverage is the honest headline number: an analysis that links 22% of
    polygons must say so, never imply full coverage.
    """
    index = alias_index(companies)
    groups = concessions[group_column].fillna("No group").astype(str)
    linked = groups.map(lambda g: index.get(g.strip().casefold()))
    total = len(groups)
    linked_count = int(linked.notna().sum())
    return {
        "polygons_total": total,
        "polygons_linked": linked_count,
        "coverage_pct": round(100.0 * linked_count / total, 1) if total else 0.0,
        "per_parent": {k: int(v) for k, v in linked.dropna().value_counts().items()},
        "top_unlinked": {
            k: int(v)
            for k, v in groups[linked.isna()].value_counts().head(top_unlinked).items()
        },
    }


# --- reporting ---------------------------------------------------------------


def build_report(companies: dict[str, CompanyFile], concessions_path: Path | None) -> dict:
    entries = []
    for ticker, company in companies.items():
        statement = latest_statement(company)
        entries.append(
            {
                "ticker": ticker,
                "name": company.parent.name,
                "exchange": company.parent.exchange,
                "currency": company.parent.reporting_currency,
                "period": statement.period,
                "metrics": metrics(statement),
            }
        )
    report: dict[str, Any] = {"companies": entries}
    if concessions_path is not None:
        import pandas as pd

        report["coverage"] = attribution_coverage(
            pd.read_parquet(concessions_path), companies
        )
    return report


def _print_report(report: dict) -> None:
    if not report["companies"]:
        print("no company files found - copy private/companies/_template.yaml and fill it in")
    for entry in report["companies"]:
        m = entry["metrics"]
        nd = m["net_debt_to_ebitda"]
        print(
            f"{entry['ticker']:>6}  {entry['name']}  ({entry['exchange']}, "
            f"{entry['currency']})  {entry['period']}  "
            f"net_debt={m['net_debt']:.1f}  ND/EBITDA={nd if nd is None else round(nd, 2)}"
        )
    coverage = report.get("coverage")
    if coverage:
        print(
            f"\ncoverage: {coverage['polygons_linked']}/{coverage['polygons_total']} "
            f"polygons linked ({coverage['coverage_pct']}%)  per_parent={coverage['per_parent']}"
        )
        print(f"top unlinked groups: {coverage['top_unlinked']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="link_ownership", description="Private listed-company linkage report."
    )
    parser.add_argument("--companies", required=True, help="directory of hand-sourced YAML")
    parser.add_argument("--concessions", default=None, help="plantation_polygons.parquet")
    parser.add_argument("--out", default=None, help="write the JSON report to this path")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a summary")
    args = parser.parse_args(argv)

    companies = load_companies(Path(args.companies))
    concessions_path = Path(args.concessions) if args.concessions else None
    report = build_report(companies, concessions_path)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"wrote {out}")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
