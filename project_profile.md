# Project Specification: Geospatial Climate Risk Intelligence Platform

## 1. Project Objective

Build an end-to-end, AI-powered geospatial climate-risk intelligence platform designed for **banks and insurance companies**, initially focused on wildfire and haze risks arising from Indonesia.

The platform should combine:

- Satellite imagery and remote sensing
- Computer vision and image segmentation
- Machine learning for wildfire prediction
- Geospatial analysis and concession boundary mapping
- Synthetic corporate ownership and financial statements
- Credit risk and insurance exposure modelling
- Interactive risk monitoring and explainable AI

**Core business objective:** Translate real environmental hazards into measurable financial risk indicators that financial institutions can use for credit monitoring, underwriting, portfolio surveillance, and early warning.

The platform is an independent research prototype, not a production credit-rating or insurance-pricing system.

## 2. Target Customers and Business Cases

### A. Banking — Climate-Adjusted Credit Risk

Target users:
- Corporate credit risk officers
- Relationship managers
- Portfolio risk managers
- Climate and ESG risk teams

Business questions:

1. Which borrowers have plantation or industrial assets exposed to current wildfire activity?
2. Which geographic regions exhibit increasing wildfire probability?
3. How would hypothetical wildfire disruptions affect borrowers' EBITDA, cash flows, leverage, and debt-servicing capacity?
4. Which borrowers require enhanced monitoring?
5. Where are concentrations of climate-related physical risk across the portfolio?

Expected outputs:
- Borrower exposure dashboard
- Geospatial hotspot and asset overlay
- Fire-risk forecasts
- Scenario-based financial stress tests
- Credit early-warning indicators
- Portfolio concentration analytics

### B. Insurance — Wildfire Underwriting and Portfolio Risk

Target users:
- Commercial property underwriters
- Catastrophe risk analysts
- Reinsurers
- Portfolio accumulation managers

Business questions:

1. Which insured assets are exposed to active or forecast wildfire activity?
2. How much insured value is geographically concentrated in high-risk areas?
3. How might hypothetical wildfire scenarios affect expected claims?
4. Which policies warrant underwriting review?
5. How do alternative hazard scenarios affect portfolio losses?

Expected outputs:
- Geospatial insured-asset exposure map
- Fire-risk overlay
- Total insured value at risk
- Scenario-based estimated insured losses
- Geographic accumulation analysis
- Underwriting review alerts

Do not claim that the platform calculates actuarially validated premiums or reserves.

## 3. Data Strategy

**Real environmental data, synthetic commercial and financial data.**

| Dataset | Source | Treatment |
|---|---|---|
| Active fire hotspots | NASA FIRMS (VIIRS/MODIS) | Real |
| Multispectral imagery | Sentinel-2 / Landsat | Real |
| Weather and precipitation | ERA5 / Open-Meteo | Real |
| Vegetation and land cover | Copernicus / public datasets | Real |
| Peatland and soil characteristics | Public geospatial sources | Real |
| Plantation and concession boundaries | Publicly available polygon datasets | Real internally, anonymized or aggregated publicly |
| Corporate ownership relationships | Synthetic | Entirely fictional |
| Corporate financial statements | Synthetic | Entirely fictional |
| Bank lending exposure | Synthetic | Entirely fictional |
| Insurance policies | Synthetic | Entirely fictional |
| Asset values and insured amounts | Synthetic | Entirely fictional |

### Critical requirements

- Never use confidential banking data.
- Never copy real company statements and simply change the names.
- Generate synthetic, internally consistent balance sheets, income statements and cash flow statements.
- Ensure financial statements reconcile.
- Never imply that a fictional borrower is a real bank's customer.
- Avoid re-identification through exact concession coordinates, ownership records, or polygon geometry displayed publicly.
- Do not infer culpability or fire causation merely from geographic overlap.
- Record dataset provenance, licensing, acquisition date, spatial resolution, and observation timestamps.

## 4. Computer Vision and Geospatial ML

Build separate, testable capabilities.

### Model A — Fire and Burned-Area Segmentation

Candidates:
- U-Net
- SegFormer
- SAM 2 for assisted labeling and segmentation

Purpose:
- Identify burned areas from satellite imagery.
- Estimate impacted land area.
- Monitor vegetation changes.
- Compare imagery before and after fire events.

Use multispectral indices such as NDVI and NBR/dNBR as interpretable baselines.

Important: Fire hotspots and smoke visibility are not equivalent to confirmed burned area.

### Model B — Wildfire Escalation Prediction

Initial algorithms:
- Random Forest
- XGBoost

Potential features:
- Recent hotspot activity
- Fire radiative power
- Rainfall
- Temperature
- Relative humidity
- Wind speed and direction
- Soil moisture
- Vegetation conditions
- Peatland classification
- Historical fire occurrence
- Drought indicators

Forecast horizons:
- 24 hours
- 48 hours
- 72 hours

Predict calibrated probabilities of fire persistence, escalation or new hotspot occurrence under explicitly defined target labels.

Compare against simple historical and persistence baselines.

Evaluation:
- Precision and recall
- PR-AUC
- Brier score and probability calibration
- False alert rates
- Spatial and temporal holdout performance
- Lead time gained relative to baseline

Prevent future-data leakage. Use observation availability timestamps and geographic holdout regions.

### Model C — Concession Boundary and Exposure Mapping

Use:
- GeoPandas
- Shapely
- PostGIS
- Rasterio

Capabilities:
- Load available concession polygons.
- Perform point-in-polygon spatial joins.
- Calculate hotspot counts and fire exposure near polygons.
- Calculate distance to fire activity.
- Overlay burned-area estimates.
- Aggregate exposure by geographic region.
- Capture boundary uncertainty.

Use existing published concession polygons for legal or administrative boundaries.

**Do not treat boundaries inferred by a vision model as legally verified property or concession boundaries.**

Public concession boundaries may be incomplete or outdated. Preserve dataset vintages and document attribution uncertainty.

## 5. Synthetic Financial Data Engine

Create reproducible synthetic companies representing:

- Palm oil producers
- Pulp and paper businesses
- Agricultural commodity companies
- Forestry businesses
- Industrial operators

Each fictional company should have:

- Company ID and fictional name
- Industry and geographic footprint
- Synthetic plantation or operating assets
- Revenue and operating expenses
- EBITDA
- Cash and cash equivalents
- Short-term debt
- Long-term debt
- Interest expense
- Capital expenditure
- Operating cash flow
- Total assets, liabilities and equity
- Debt maturity profile

Financial statements must satisfy:

**Assets = Liabilities + Equity**

Cash-flow movements should reconcile with opening and closing cash balances.

Build several years of synthetic historical statements to support trend analysis.

Generate distinct archetypes, such as highly leveraged producers, cash-rich diversified operators, and geographically concentrated borrowers.

All values must be visibly labeled as synthetic.

## 6. Bank Credit Risk Analytics

Connect environmental hazard scenarios to hypothetical company financial outcomes.

### Baseline financial metrics

- Net debt / EBITDA
- Debt / equity
- EBITDA / interest expense
- Current ratio
- Operating cash flow / total debt
- Liquidity runway
- Debt maturity concentration

### Scenario modelling

User-adjustable assumptions:
- Percentage of productive land affected
- Production disruption
- Revenue reduction
- Operating cost increase
- Recovery duration
- Remediation cost
- Working capital impact

Simulate resulting changes in:
- EBITDA
- Operating cash flow
- Net leverage
- Interest coverage
- Liquidity
- Credit monitoring status

Potential portfolio indicators:
- Borrowers near modeled fire activity
- Synthetic exposure associated with high-hazard regions
- Borrowers experiencing modeled covenant pressure
- Portfolio concentration by sector and geography

### Expected credit loss

For illustrative purposes:

ECL = PD × LGD × EAD

Where:
- PD = Probability of Default
- LGD = Loss Given Default
- EAD = Exposure at Default

Use synthetic or explicitly illustrative PD, LGD, and EAD.

Do not claim that environmental hazard scores are validated PD estimates. Keep hazard scoring and credit calibration separate.

## 7. Insurance Risk Analytics

Generate synthetic insurance portfolios containing:

- Policy ID
- Fictional policyholder
- Asset category and location
- Total insured value
- Policy limit
- Deductible
- Coverage type
- Policy inception and expiry
- Geographic concentration

### Initial analytics

- Insured values near active hotspots
- Exposure by region
- Risk accumulation across policies
- Hypothetical damage ratios
- Scenario-based gross and net claims
- Losses subject to simplified deductibles and limits

Clearly specify the order of policy calculations and assumptions.

Do not present estimated insurance losses as validated catastrophe-model outputs without historical claims validation.

## 8. Proposed Architecture

### Frontend

- React
- TypeScript
- Tailwind CSS
- MapLibre GL JS
- Charts and interactive tables

Core pages:

1. Executive Risk Dashboard
2. Live Fire and Haze Monitoring Map
3. Fire Forecasting Dashboard
4. Concession and Geographic Exposure
5. Synthetic Company Risk Profiles
6. Credit Risk Stress Testing
7. Insurance Accumulation and Loss Scenarios
8. Model Evaluation and Data Provenance

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL with PostGIS

API capabilities:
- Fire observation retrieval
- Historical fire queries
- Geospatial intersection and buffering
- Forecast retrieval
- Burned-area estimates
- Synthetic company financial statements
- Credit scenario calculations
- Insurance scenario calculations
- Portfolio analytics
- Data and model provenance

### Data and ML

- GeoPandas, Shapely, Rasterio
- PyTorch for computer vision
- scikit-learn and XGBoost
- Parquet/GeoParquet for historical observations
- MLflow for experiment tracking and model versioning

Use batch ingestion and scheduled inference initially. Do not introduce Kafka or real-time streaming unless justified by measurable latency requirements.

### Deployment

- Docker Compose for local development
- Containerized FastAPI backend
- Containerized PostgreSQL/PostGIS
- Static React frontend
- Scheduled Python ingestion/inference jobs
- Optional Hugging Face Spaces demonstration using a reduced public dataset

Avoid placing sensitive credentials or proprietary data in the frontend.

Use only public or synthetic inputs in the demo.

## 9. End-to-End Processing Workflow

1. Collect real satellite hotspot observations.
2. Ingest weather, land-cover and peatland observations.
3. Normalize coordinate systems and timestamps.
4. Load and quality-check public concession polygons.
5. Detect and segment burned areas where imagery is available.
6. Predict near-term fire escalation probabilities.
7. Spatially associate hazard observations with geographic assets.
8. Join assets to entirely synthetic corporate ownership structures.
9. Calculate credit and insurance exposure indicators.
10. Run user-defined financial stress scenarios.
11. Generate interactive dashboard views and alerts.
12. Record source data, assumptions, model versions and calculation traces.

## 10. Risk and Governance Requirements

Because the project is being developed independently by someone employed in banking, enforce strict separation from employer systems and confidential information.

Mandatory safeguards:

- Do not use employer data, credentials, code or infrastructure without explicit authorization.
- Avoid using employer-specific credit policies, internal ratings or proprietary models.
- Use synthetic borrowers and insurers.
- Label all synthetic datasets, scenarios and financial estimates.
- Clearly distinguish observed events, forecasts and hypothetical losses.
- Display uncertainty and prediction confidence where meaningful.
- Include source citations and model documentation.
- Ensure public-facing data cannot easily reconstruct purported fictional company relationships from actual concession ownership.
- Apply rate limits, input validation and secure secret management.
- Do not publish unsupported claims about real companies.
- Include a research disclaimer.
- Review applicable employment, intellectual-property and outside-business-activity policies before public release.

## 11. Testing and Evaluation

Implement automated testing from the beginning.

### Data tests
- Coordinate reference system consistency
- Valid polygon geometry
- Duplicate hotspot detection
- Temporal alignment
- Data availability and missingness
- Synthetic accounting reconciliation

### ML tests
- No training/test temporal leakage
- Spatial holdout validation
- Forecast calibration
- Baseline comparison
- Model version reproducibility

### Financial model tests
- Balance sheet reconciliation
- Cash-flow reconciliation
- Scenario calculation consistency
- Loan and policy exposure aggregation
- Insurance limit and deductible calculations
- Edge cases and invalid scenario inputs

### Application tests
- Unit tests using pytest
- FastAPI integration tests
- Frontend component tests
- End-to-end smoke tests
- GitHub Actions CI/CD

Maintain an evaluation dashboard showing actual validation performance rather than unsubstantiated accuracy claims.

## 12. Implementation Roadmap

### Phase 1 — Minimum Viable Product

Prioritize completion of one end-to-end workflow.

Deliver:
- Historical NASA FIRMS observations
- Indonesian fire map
- Public concession polygon overlay
- Synthetic company and asset mapping
- Synthetic financial statements
- Basic borrower risk dashboard
- Rule-based or baseline hazard scoring
- One reproducible credit stress scenario

**Success criterion:** A user selects a fictional borrower, sees its geographic asset exposure to real environmental observations, runs a hypothetical fire-loss scenario, and receives an explainable financial risk assessment.

### Phase 2 — Predictive Machine Learning

Deliver:
- Historical weather and vegetation features
- XGBoost fire-risk forecasting
- Temporal and spatial backtesting
- Model calibration
- 24–72-hour fire escalation forecasts
- Risk alerts based on measured thresholds

### Phase 3 — Computer Vision

Deliver:
- Multispectral imagery processing
- Burned-area segmentation
- Before/after imagery comparisons
- Burned-area model evaluation
- Integration of observed damage estimates into geographic exposure analysis

### Phase 4 — Insurance Analytics

Deliver:
- Synthetic insurance policies
- Geographic aggregation of sums insured
- Exposure accumulation dashboard
- Hypothetical damage and claim scenarios
- Underwriting review workflow

### Phase 5 — Production Engineering

Deliver:
- Scheduled ingestion and inference
- Model monitoring
- Data quality monitoring
- Authentication and authorization
- Application observability
- Deployment automation
- Security and performance testing

Do not build every feature simultaneously. Prioritize a working vertical slice and measurable model quality.

## 13. Required Deliverables from Codex

1. Proposed repository structure.
2. System architecture and data-flow diagram.
3. Data model and database schema.
4. API contract.
5. Reproducible synthetic financial-data generator.
6. Geospatial ingestion and processing pipeline.
7. Baseline wildfire exposure calculation.
8. Functional React dashboard.
9. Credit stress-testing engine.
10. Test suite and CI configuration.
11. Dockerized local environment.
12. Deployment documentation.
13. Model evaluation methodology.
14. Data-source and licensing register.
15. Clear README describing what works, what is experimental, and what has not yet been implemented.

## 14. Codex Execution Instructions

Act as the principal software engineer, geospatial ML engineer, and financial risk systems architect.

Start by auditing the existing repository and identifying whether a wildfire/haze vision model, preprocessing pipeline, training data, tests or deployment configuration already exists.

Reuse working components where appropriate. Do not overwrite or duplicate existing functionality.

Before implementing, produce:
- A gap analysis
- A prioritized build plan
- Architectural decisions and trade-offs
- Definition of done for Phase 1

Then implement Phase 1 with tests.

Prefer established libraries and straightforward designs over unnecessary abstraction or multi-agent complexity.

Make the application demonstrable locally using documented commands.

Do not fabricate environmental observations, model evaluation results, or completed functionality. Synthetic financial data must be explicitly identified.

The goal is an auditable, technically credible financial risk prototype—not merely a visually attractive satellite dashboard.

## 15. Final Product Positioning

**Geospatial Climate Risk Intelligence for Financial Institutions**

A platform that uses remote sensing, machine learning and geospatial analysis to translate wildfire activity into actionable credit and insurance risk intelligence.

Initial geography: Indonesia.

Initial hazard: Wildfire and associated haze.

Initial sectors: Palm oil, forestry, pulp and paper, agricultural commodities.

Primary buyers: Commercial banks and specialty insurers.

Public demonstration: Real environmental observations paired with entirely synthetic companies, financial statements, bank exposures and insurance policies.

Long-term opportunity: Expand into flood, drought, extreme heat, and multi-hazard climate risk monitoring across Southeast Asia.