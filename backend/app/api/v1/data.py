"""Precomputed data endpoints for the dashboards.

Reads pipeline outputs (Parquet/GeoJSON) written by `haze-pipelines` and serves
them as JSON - no per-request computation, consistent with the architecture
brief ("serve precomputed environmental observations and forecasts where
possible").

All payloads carry data-treatment labels so the UI can distinguish observed,
derived and synthetic-fixture data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter(tags=["data"])


def _require(path: Path) -> Path:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"dataset not available: {path}. Run the ingestion pipeline first "
            "(see docs/pipeline.md).",
        )
    return path


@router.get("/fires/hotspots")
def fire_hotspots(limit: int = 500) -> dict:
    """Hotspot detections (pipeline dataset; treatment label included)."""
    path = _require(settings.data_dir / "processed" / "fire_hotspots.parquet")
    df = pd.read_parquet(path).head(limit)
    is_fixture = bool(df["is_fixture"].any()) if len(df) else False
    return {
        "treatment": "synthetic-fixture" if is_fixture else "real",
        "caveat": "Satellite fire detections, not confirmed burned area or causation.",
        "count": len(df),
        "features": [
            {
                "hotspot_id": row.hotspot_id,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "observation_time": str(row.observation_time),
                "confidence_pct": None if pd.isna(row.confidence_pct) else float(row.confidence_pct),
                "frp_mw": None if pd.isna(row.frp_mw) else float(row.frp_mw),
                "source": row.source,
                "is_fixture": bool(row.is_fixture),
            }
            for row in df.itertuples()
        ],
    }


@router.get("/exposure/public")
def public_exposure() -> dict:
    """Anonymized, simplified concession exposure layer (safe to display)."""
    path = _require(settings.data_dir / "processed" / "exposure_public.geojson")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/exposure/summary")
def exposure_summary() -> dict:
    path = _require(settings.data_dir / "processed" / "exposure.summary.json")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/forecasts")
def forecasts(horizon_hours: int | None = 24, limit: int = 50) -> dict:
    """Baseline hazard scores (labeled baseline - not a validated forecast)."""
    path = _require(settings.data_dir / "processed" / "forecast_baseline.parquet")
    df = pd.read_parquet(path)
    if horizon_hours is not None:
        df = df[df["horizon_hours"] == horizon_hours]
    df = df.sort_values("hazard_score", ascending=False).head(limit)

    exposure_path = settings.data_dir / "processed" / "exposure.parquet"
    detections: dict[str, int] = {}
    areas: dict[str, float] = {}
    if exposure_path.exists():
        exposure = pd.read_parquet(exposure_path)
        detections = dict(
            zip(exposure["polygon_id"], exposure["hotspot_count_in_polygon_30d"].astype(int))
        )
        areas = dict(zip(exposure["polygon_id"], exposure["area_ha"].astype(float)))

    first = df.iloc[0] if len(df) else None
    return {
        "model_name": first["model_name"] if first is not None else None,
        "model_version": first["model_version"] if first is not None else None,
        "data_type": first["data_type"] if first is not None else None,
        "disclaimer": first["disclaimer"]
        if first is not None
        else "Baseline hazard score - not a calibrated probability or a PD.",
        "rows": [
            {
                "polygon_id": row.polygon_id,
                "as_of": str(row.as_of),
                "horizon_hours": int(row.horizon_hours),
                "hazard_score": float(row.hazard_score),
                "detections_30d": detections.get(row.polygon_id, 0),
                "area_ha": areas.get(row.polygon_id),
            }
            for row in df.itertuples()
        ],
    }
