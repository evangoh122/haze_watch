# Data Model and Database Schema

> Status: outline only. Full DDL to be written in Phase 1 alongside the SQLAlchemy models.

Conventions:

- All geometry columns use PostGIS `geometry` with SRID 4326 (WGS84); convert on ingest.
- All tables carry `created_at` / `updated_at`.
- Every synthetic row is labeled `is_synthetic = true` and carries a `generator_version`.
- Observation tables carry `observation_time` (when measured) and `available_time`
  (when it became publicly available) to prevent future-data leakage in training.

## Planned tables

### Environmental (real)

| Table | Purpose | Key columns |
|---|---|---|
| `fire_hotspots` | FIRMS VIIRS/MODIS active fire detections | hotspot_id, source, lat, lon, acq_time, available_time, frp, brightness, confidence, daynight |
| `weather_observations` | ERA5 / Open-Meteo gridded weather | station_id, lat, lon, observation_time, available_time, temp_max, precip, humidity, wind_max |
| `haze_aerosol` | CAMS / Open-Meteo haze indicators (not fire detections) | grid_id, date, available_time, lat, lon, aod_mean, aod_max, pm2_5, pm10, source |
| `land_cover` | Copernicus land cover / vegetation | geom, class_code, vintage, source |
| `peatlands` | Peatland / soil characteristics | geom, peat_depth, vintage, source |
| `concessions` | Published plantation/concession polygons | concession_id, geom, boundary_type, vintage, attribution_confidence, source, license |
| `burned_areas` | Model/derived burned-area estimates | geom, observed_or_predicted, model_version, confidence |

### Commercial (entirely synthetic)

| Table | Purpose | Key columns |
|---|---|---|
| `companies` | Fictional companies | company_id, fictional_name, industry, archetype, is_synthetic |
| `company_assets` | Synthetic plantation/operating assets | asset_id, company_id, geom, area_ha, productive_share |
| `ownership` | Synthetic ownership structure | parent_id, child_id, stake_pct |
| `financial_statements` | Annual/quarterly statements | company_id, period, revenue, opex, ebitda, cash, st_debt, lt_debt, interest, capex, ocf, total_assets, total_liabilities, total_equity |
| `debt_maturities` | Debt maturity profile | company_id, period, amount |
| `bank_exposures` | Synthetic lending exposure | exposure_id, company_id, facility_type, ead, limit, maturity |
| `insurance_policies` | Synthetic policies | policy_id, policyholder (fictional), asset_id, tiv, limit, deductible, coverage_type, inception, expiry |

### Risk, model and provenance

| Table | Purpose | Key columns |
|---|---|---|
| `hazard_scores` | Baseline/modelled hazard per asset/region | geom or asset_id, score, method, model_version, computed_at |
| `forecast_runs` | Fire escalation forecasts | run_id, horizon_h, issued_at, valid_from, model_version |
| `scenario_runs` | Credit/insurance scenario executions | run_id, assumptions_json, results_json, computed_at, trace |
| `datasets` | Dataset provenance register | name, source, license, acquired_at, spatial_resolution, vintage |
| `model_versions` | MLflow model registry mirror | model_name, version, run_id, metrics_json |

## Reconciliation invariants (synthetic data)

- `total_assets = total_liabilities + total_equity` for every statement period.
- Cash-flow statement: `opening_cash + net_change = closing_cash`, and `closing_cash(t) = opening_cash(t+1)`.
