# Private research data — real listed companies. DO NOT PUBLISH.

This directory links **real** Indonesian concession boundaries (which carry an
`unverified` group attribution) to their **listed parent companies**, and reads
**hand-entered** financial statements sourced from public filings (SGXNet / IDX /
Bursa Malaysia annual reports). It is deliberately separate from the public demo,
which stays on anonymized/aggregated boundaries + synthetic companies.

Read `docs/governance.md` first. The rules that apply here in full:

- Nothing produced here is published, screenshotted or committed.
- Every figure needs a citation; entries without one are rejected by validation.
- Geographic overlap between a fire detection and a concession is **not** evidence
  of causation, culpability or responsibility.
- Attribution stays `unverified` until a filing (or RSPO / SPOTT / Trase) confirms
  the parent-subsidiary link.
- No named public claims. Internal research only.

## Layout

```
private/
├── link_ownership.py            loader + validation + metrics + coverage (tracked)
├── companies/
│   ├── _template.yaml           schema to copy (tracked)
│   └── <TICKER>.yaml            filled by hand — GITIGNORED, never commit
├── out/                         generated reports — GITIGNORED
└── tests/test_link_ownership.py synthetic-fixture tests (tracked)
```

## Hand-source workflow

1. **Verify the link.** For an Indonesian concession holder (`company_attribution`
   like `PT ...`), confirm the path to the listed parent in the annual report
   (subsidiary list / notes), or via RSPO ACOP, SPOTT or Trase. Record it under
   `ownership` with `stake_pct`, `as_of` and a `source_ref`.
2. **Read the consolidated figures** for the parent from the filing (income
   statement, balance sheet, cash-flow, borrowings note) and enter 3–5 years,
   oldest first, in the parent's reporting currency (millions).
3. **Cite everything.** Add one `citations` entry per source and point each
   statement / ownership row at it via `source_ref`.
4. **Run it:**
   ```bash
   python private/link_ownership.py \
       --companies private/companies \
       --concessions data/processed/plantation_polygons.parquet
   ```
   Validation enforces `total_assets == total_liabilities + total_equity` and
   `ebitda == revenue - cash_opex`, so typos are caught before any analysis.

Keep the balance sheet in mind: the leverage you care about is at the **listed
parent** (consolidated), and SGX agri groups often report in **USD** while their
Indonesian subsidiaries report in **IDR** — consolidate, never add.

## Coverage is the honest headline

From the current 300-polygon BNPB/GFW layer, **78% of polygons carry
`group_attribution = "No group"`**, so any parent-level analysis covers a
minority of boundaries. Report the coverage number next to every result; never
imply full coverage.

Which groups to verify first is a **research decision, not repo content**: real
issuer names and parent-subsidiary mappings belong only in the gitignored
`companies/<TICKER>.yaml` files (and in whatever internal notes you keep outside
this repository). Do not add them here or to any other tracked file.

## Tests

```bash
python -m pytest private/tests
```

The tests use an invented fixture company; nothing real is required or fabricated.
