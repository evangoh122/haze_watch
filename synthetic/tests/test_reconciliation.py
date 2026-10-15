"""Reconciliation tests for the synthetic financial data engine.

The engine itself is not implemented yet (``synthetic/`` contains stubs only).
These tests document the invariants the engine MUST satisfy and are skipped
until it exists - they keep CI honest (no false green, no false red).
"""

import pytest

pytestmark = pytest.mark.skip(reason="synthetic financial engine not implemented yet")


def test_balance_sheet_identity():
    """Assets = Liabilities + Equity for every generated statement period."""


def test_cash_flow_rollforward():
    """opening_cash + net_change_in_cash = closing_cash, and cash rolls across periods."""


def test_all_outputs_labeled_synthetic():
    """Every generated row carries is_synthetic=True and a generator_version."""
