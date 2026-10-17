# Governance, Risk and Disclaimers

## Research disclaimer (must appear in the UI and README)

This platform is an independent research prototype. It is not a production
credit-rating, insurance-pricing, or catastrophe-modelling system. Environmental
observations are real; the demo application's companies, ownership structures,
financial statements, bank exposures and insurance policies are entirely
synthetic and fictional - nothing in the demo layer describes, implicates, or
is derived from any real company's financial position, any real bank's
customers, or any real insurer's book. Research-phase analysis may use real,
named companies' **public regulatory filings** (see "Real named fundamentals"
below); those outputs are separately labeled, cite the underlying filing, and
carry no investment advice or predictive claims.

## Real named fundamentals (research phase - admitted 2026-10-17)

The modeling phase joins the environmental hazard panel to **real, named,
public-filing fundamentals**. This is the one place the all-synthetic rule does
not apply, and it is bounded as follows:

- **Public filings only**: SEC EDGAR and IDX regulatory filings (annual/
  quarterly reports, XBRL where available). No paid terminals, no scraped
  private data, no leaked or employer-derived data.
- **Full traceability**: every figure carries the issuer name, the filing
  reference (form/report type + filing date), and the retrieval date. A figure
  without a filing reference may not be published.
- **Claims discipline**: with a handful of public filers and no loan-level
  outcomes, the deliverable is an **event-study / attribution and sensitivity
  analysis** around the 2015, 2019 and 2023-24 El Nino fire seasons - **not a
  predictive model**. No accuracy/R-squared style metrics may be reported
  without out-of-sample validation, and none is planned in this phase.
- **No advice**: nothing produced is investment advice, valuation, a
  recommendation, or a credit rating.
- **No mixing without labels**: synthetic demo figures must never appear
  alongside real filing figures without both being labeled; joins between the
  hazard panel and real fundamentals are analytic overlays and must say so.
- **Licence care**: SEC filing data may be used and quoted with attribution;
  IDX materials' redistribution terms must be verified before anything beyond
  derived aggregates leaves the machine (same posture as the concession
  geometry: verify before redistribution).

## Mandatory safeguards

- No employer data, credentials, code, policies, internal ratings, proprietary models
  or infrastructure may be used without explicit authorization.
- All synthetic datasets, scenarios and financial estimates must be visibly labeled.
- Observed events, forecasts and hypothetical losses must be clearly distinguished,
  with uncertainty and prediction confidence shown where meaningful.
- Source citations and model documentation accompany all published outputs.
- Public-facing data must not allow reconstruction of purported fictional company
  relationships from actual concession ownership.
- No unsupported claims about real companies may be published. With real-filing
  analysis this tightens: every claim must be traceable to the cited filing.
- Fire hotspots and smoke visibility are not equivalent to confirmed burned area, and
  geographic overlap is not evidence of fire causation or culpability.
- Boundaries inferred by vision models are not legally verified property or concession
  boundaries.
- Estimated insurance losses are not validated catastrophe-model outputs and no
  actuarially validated premiums or reserves are calculated.
- Environmental hazard scores are not validated PD estimates.
- Rate limits, input validation and secure secret management are required.

## Pre-release checklist

- [ ] Review applicable employment, intellectual-property and outside-business-activity
      policies before any public release.
- [ ] Confirm licensing and attribution for every external dataset.
- [ ] Verify re-identification risk on all public geometry and ownership outputs.
- [ ] Confirm every synthetic artifact is labeled in UI, API and data files.
- [ ] Confirm every real-filing figure carries issuer + filing reference + retrieval date.
- [ ] Confirm no output mixes synthetic and real figures without both labels.
