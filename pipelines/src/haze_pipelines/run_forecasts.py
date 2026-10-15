"""Baseline fire-risk forecast (persistence / recency heuristic).

This is an **explicitly labeled baseline**, not a trained model. It exists so that
future ML models (XGBoost, Phase 2) have a measurable floor to beat. The formula
is deterministic and documented; no accuracy claims are made anywhere.

Rule (documented, deterministic):
    score = 0.6 * recency + 0.4 * intensity
where
    recency    = exp(-days_since_last_hotspot / 7)   (0 when no hotspot in window)
    intensity  = min(hotspot_count_30d / 10, 1)
Output is a 0-1 *hazard score*, NOT a calibrated probability and NOT a PD.
"""

from __future__ import annotations

import math

import pandas as pd

from .config import settings
from .io import read_geo_metadata, read_parquet, write_parquet
from .provenance import derive_treatment, register_dataset

BASELINE_NAME = "persistence_recency_baseline"
BASELINE_VERSION = "0.1.0"

FORECAST_COLUMNS = [
    "polygon_id",
    "as_of",
    "horizon_hours",
    "hazard_score",
    "model_name",
    "model_version",
    "data_type",
    "disclaimer",
]

DISCLAIMER = (
    "Baseline hazard score (0-1), not a calibrated probability, not a validated "
    "fire forecast, and not a probability of default."
)


def hazard_score(days_since_last_hotspot: float | None, hotspot_count_30d: int) -> float:
    if days_since_last_hotspot is None or pd.isna(days_since_last_hotspot):
        recency = 0.0
    else:
        recency = math.exp(-max(0.0, float(days_since_last_hotspot)) / 7.0)
    intensity = min(max(hotspot_count_30d, 0) / 10.0, 1.0)
    return round(0.6 * recency + 0.4 * intensity, 4)


def run_forecast(
    features_path,
    out_path,
    *,
    horizons_hours: tuple[int, ...] = (24, 48, 72),
    settings_obj=settings,
) -> tuple[pd.DataFrame, object]:
    """Score every polygon from a feature table and persist forecast rows."""
    features = read_parquet(features_path)

    rows = []
    for _, row in features.iterrows():
        score = hazard_score(row.get("days_since_last_hotspot"), int(row.get("hotspot_count_30d", 0)))
        for horizon in horizons_hours:
            rows.append(
                {
                    "polygon_id": row["polygon_id"],
                    "as_of": row["as_of"],
                    "horizon_hours": horizon,
                    "hazard_score": score,
                    "model_name": BASELINE_NAME,
                    "model_version": BASELINE_VERSION,
                    "data_type": "baseline",
                    "disclaimer": DISCLAIMER,
                }
            )

    df = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    write_parquet(df, out_path, extra_metadata={"dataset": "fire_forecast_baseline"})

    # Treatment is inherited from the feature inputs recorded in their metadata;
    # unknown provenance must surface as "derived-unverified", never as "real".
    features_meta = read_geo_metadata(features_path)
    treatment = derive_treatment(features_meta.get("treatment"))

    register_dataset(
        settings_obj.metadata_dir,
        dataset_id=f"forecast_baseline::{BASELINE_VERSION}",
        name="Fire hazard baseline scores",
        source=str(features_path),
        license="derived from registered inputs",
        treatment=treatment,
        path=out_path,
        row_count=len(df),
        notes=DISCLAIMER,
    )
    return df, out_path
