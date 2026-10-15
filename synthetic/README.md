# Synthetic Financial Data Engine

Generates **entirely fictional** companies, ownership structures, financial
statements, bank exposures and insurance policies. No output may be derived from,
or resemble, any real company's financial statements or any real bank/insurer book.

```
synthetic/
├── companies.py     fictional companies (palm oil, pulp & paper, forestry, industrial)
├── archetypes.py    highly leveraged | cash-rich diversified | geographically concentrated
├── financials.py    income statement, balance sheet, cash flow (multi-year)
├── ownership.py     fictional ownership trees
├── loans.py         synthetic bank exposures + debt maturity profiles
├── policies.py      synthetic insurance policies (TIV, limits, deductibles)
├── reconcile.py     accounting invariant checks
├── generate.py      CLI: python -m synthetic.generate --out data/synthetic
└── tests/           reconciliation tests
```

Invariants enforced by `reconcile.py` and tested in `tests/`:

- `total_assets = total_liabilities + total_equity` for every period.
- `opening_cash + net_change_in_cash = closing_cash`, and cash rolls forward across periods.
- All outputs are labeled synthetic and carry a `generator_version` and fixed random seed
  so runs are reproducible.
