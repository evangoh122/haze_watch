"""Tests for the private listed-company linkage slice.

Uses a SYNTHETIC fixture company (invented numbers) so nothing real is needed and
nothing real is fabricated. The template file must fail validation until a human
fills it from filings.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from link_ownership import (
    attribution_coverage,
    load_companies,
    load_company_file,
    metrics,
)
from pydantic import ValidationError

TEMPLATE = Path(__file__).resolve().parents[1] / "companies" / "_template.yaml"


def _fy2024() -> dict:
    return {
        "period": "FY2024",
        "revenue": 900.0,
        "cash_opex": 700.0,
        "ebitda": 200.0,
        "interest_expense": 35.0,
        "cash": 80.0,
        "short_term_debt": 210.0,
        "long_term_debt": 410.0,
        "current_assets": 480.0,
        "current_liabilities": 290.0,
        "total_assets": 1450.0,
        "total_liabilities": 880.0,
        "total_equity": 570.0,
        "operating_cash_flow": 140.0,
        "capex": 75.0,
        "source_ref": "ar-2025",
    }


def _fy2025() -> dict:
    return {
        "period": "FY2025",
        "revenue": 1000.0,
        "cash_opex": 800.0,
        "ebitda": 200.0,
        "interest_expense": 40.0,
        "cash": 100.0,
        "short_term_debt": 200.0,
        "long_term_debt": 400.0,
        "current_assets": 500.0,
        "current_liabilities": 300.0,
        "total_assets": 1500.0,
        "total_liabilities": 900.0,
        "total_equity": 600.0,
        "operating_cash_flow": 150.0,
        "capex": 80.0,
        "source_ref": "ar-2025",
    }


def _fixture() -> dict:
    """A SYNTHETIC company that satisfies both accounting identities (oldest first)."""
    return {
        "parent": {
            "name": "Fictional Agri Holdings Ltd",
            "ticker": "ZZ1",
            "exchange": "TEST",
            "reporting_currency": "USD",
            "fiscal_year_end": "12-31",
            "aliases": ["Fictional Group", "FG"],
        },
        "ownership": [
            {
                "parent": "Fictional Agri Holdings Ltd",
                "subsidiary": "PT Fictional Sawit",
                "stake_pct": 92.4,
                "as_of": "2025-12-31",
                "source_ref": "ar-2025",
            }
        ],
        "statements": [_fy2024(), _fy2025()],
        "facilities": [{"facility": "Term loan", "ead": 300.0, "maturity_year": 2029}],
        "citations": {
            "ar-2025": {
                "url": "https://example.test/annual-2025.pdf",
                "page": "120",
                "retrieved_on": "2026-10-16",
                "note": "illustrative fixture, not a real filing",
            }
        },
    }


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / f"{data['parent']['ticker']}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_loads_and_computes_metrics(tmp_path):
    company = load_company_file(_write(tmp_path, _fixture()))
    m = metrics(company.statements[-1])  # newest period (FY2025)
    assert m["net_debt"] == 200.0 + 400.0 - 100.0
    assert m["net_debt_to_ebitda"] == pytest.approx(2.5)
    assert m["interest_coverage"] == pytest.approx(5.0)
    assert m["current_ratio"] == pytest.approx(500.0 / 300.0)
    assert m["liquidity_runway_months"] is None  # positive operating cash flow


def test_metrics_return_none_when_not_meaningful(tmp_path):
    data = _fixture()
    newest = data["statements"][-1]
    newest["revenue"] = 795.0  # keep ebitda = revenue - cash_opex (795 - 800)
    newest["ebitda"] = -5.0
    newest["interest_expense"] = 0.0
    company = load_company_file(_write(tmp_path, data))
    m = metrics(company.statements[-1])
    assert m["net_debt_to_ebitda"] is None
    assert m["interest_coverage"] is None


def test_balance_sheet_identity_is_enforced(tmp_path):
    data = _fixture()
    data["statements"][0]["total_equity"] += 100.0  # 1500 != 900 + 670
    with pytest.raises(ValidationError, match="total_assets"):
        load_company_file(_write(tmp_path, data))


def test_ebitda_identity_is_enforced(tmp_path):
    data = _fixture()
    data["statements"][0]["ebitda"] = 250.0  # != 900 - 700
    with pytest.raises(ValidationError, match="ebitda"):
        load_company_file(_write(tmp_path, data))


def test_missing_citation_is_rejected(tmp_path):
    data = _fixture()
    data["statements"][0]["source_ref"] = "not-cited"
    with pytest.raises(ValidationError, match="not defined under citations"):
        load_company_file(_write(tmp_path, data))


def test_template_is_not_real_data():
    """The shipped template is intentionally invalid until a human fills it in."""
    with pytest.raises(ValidationError):
        load_company_file(TEMPLATE)


def test_load_companies_skips_templates(tmp_path):
    _write(tmp_path, _fixture())
    (tmp_path / "_template.yaml").write_text("parent: {}\n", encoding="utf-8")
    companies = load_companies(tmp_path)
    assert set(companies) == {"ZZ1"}


def test_attribution_coverage_maps_aliases_and_reports_unlinked(tmp_path):
    _write(tmp_path, _fixture())
    companies = load_companies(tmp_path)
    concessions = pd.DataFrame(
        {
            "group_attribution": [
                "Fictional Group",  # alias match
                "Fictional Group",
                "FG",  # alias match
                "No group",
                "Some Other Group",  # not in this file -> unlinked
                None,  # treated as "No group"
            ]
        }
    )
    coverage = attribution_coverage(concessions, companies)
    assert coverage["polygons_total"] == 6
    assert coverage["polygons_linked"] == 3
    assert coverage["coverage_pct"] == 50.0
    assert coverage["per_parent"] == {"ZZ1": 3}
    assert coverage["top_unlinked"]["No group"] == 2
    assert coverage["top_unlinked"]["Some Other Group"] == 1
