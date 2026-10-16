# Geospatial ML

Models and evaluation for the three modelling capabilities in `project_profile.md`
section 4. Nothing is implemented yet; the layout below is the target structure.

```
ml/
├── features/      fire + weather/vegetation feature engineering
├── models/        unet.py, segformer.py (burned area) | fire_escalation.py (RF/XGBoost)
├── training/      training entry points
├── evaluation/    metrics, spatial/temporal CV, leakage checks
├── baselines/     persistence + historical baselines
└── notebooks/     exploration (never the source of truth for reported metrics)
```

Discipline:

- Every model run is tracked in MLflow with dataset vintage and split definition.
- Training features must pass `evaluation/leakage.py` checks (no data whose
  `available_time` postdates the forecast issue time).
- Models must beat the baselines in `baselines/` on identical splits before being
  reported as useful.
- Burned-area segmentation always reports the NDVI/NBR threshold baseline alongside.
