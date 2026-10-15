# Model Evaluation Methodology

> Status: outline only. No models have been trained; no metrics exist yet. This
> document defines how models will be evaluated so that later claims are backed by
> measured results on an evaluation dashboard.

## Model A — Fire / burned-area segmentation (Phase 3)

- Metrics: IoU, Dice/F1 on burned-area masks, area estimation error (ha).
- Baselines: NDVI and NBR/dNBR thresholding must be reported alongside the model.
- Split: spatial holdout by region and by fire event; never random tile splits only.
- Caveat to display: fire hotspots and smoke visibility are not confirmed burned area.

## Model B — Wildfire escalation prediction (Phase 2)

- Target labels: explicitly defined (fire persistence / escalation / new hotspot
  occurrence) at 24 h, 48 h and 72 h horizons.
- Metrics: precision, recall, PR-AUC, Brier score, reliability/calibration curves,
  false alert rate, lead time vs. baseline.
- Baselines: persistence and historical-frequency baselines must be beaten on the
  same splits before a model is called useful.
- Split discipline: temporal backtesting with geographic holdout regions. Training
  must use only data whose `available_time` precedes the forecast issue time
  (enforced by `ml/evaluation/leakage.py` checks).
- Calibration: probabilities reported as calibrated only when reliability curves and
  Brier scores demonstrate it.

## Model C — Exposure mapping (Phase 1)

- Validation: hotspot counts and distances checked against hand-computed samples;
  polygon geometry validity tests; CRS consistency tests.
- Uncertainty: boundary vintage and attribution confidence reported with results.

## Reporting rules

- Report only measured numbers from runs recorded in MLflow, with dataset vintage and
  split definition.
- Never publish accuracy claims without the accompanying evaluation configuration.
- Hazard scores are not validated PD estimates; keep hazard scoring and credit
  calibration separate in all reporting.
