"""Ingest haze/aerosol indicators (CAMS via the Open-Meteo Air Quality API).

FIRMS is fire detections, NOT haze. This module pulls the haze-relevant
atmospheric columns - aerosol optical depth (AOD) and particulate matter -
from the Copernicus Atmosphere Monitoring Service (CAMS) via Open-Meteo, so
"haze" claims are backed by an actual atmospheric source.

DEPTH: the CAMS global archive available through this route starts 2022-08-31.
For deeper history (the 2015/2019 El Nino fire years) use NASA sources with
Earthdata login: OMPS Aerosol Index (2012+) or MODIS MAIAC AOD (2000+). The
registry records this depth limit; see docs/data-sources-and-licensing.md.

Usage:
    haze-pipelines ingest-aerosol --start 2023-01-01 --end 2023-03-31
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

from .config import Settings, settings
from .geo import INDONESIA_BBOX

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HOURLY_VARS = ("aerosol_optical_depth", "pm2_5", "pm10")

CANONICAL_COLUMNS = [
    "date",
    "available_time",
    "grid_id",
    "latitude",
    "longitude",
    "aerosol_optical_depth_mean",
    "aerosol_optical_depth_max",
    "pm2_5_mean",
    "pm10_mean",
    "is_fixture",
    "source",
]

DEPTH_NOTE = (
    "Haze indicators (AOD/PM) - not fire detections and not burned area. CAMS "
    "archive via Open-Meteo starts 2022-08-31; deeper haze history (OMPS Aerosol "
    "Index 2012+, MODIS MAIAC AOD 2000+) requires NASA Earthdata credentials."
)


def fetch_point_hourly(
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 120.0,
    max_retries: int = 5,
    retry_wait_seconds: float = 60.0,
) -> dict:
    """Fetch hourly aerosol/PM values for one point. Returns the raw JSON payload."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARS),
        "start_date": start,
        "end_date": end,
        "timezone": "UTC",
    }
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        for attempt in range(max_retries + 1):
            response = client.get(API_URL, params=params, timeout=timeout)
            if getattr(response, "status_code", 200) == 429 and attempt < max_retries:
                time.sleep(retry_wait_seconds)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        else:  # pragma: no cover - defensive; loop always breaks or raises
            raise RuntimeError("unreachable: aerosol retry loop exhausted")
    finally:
        if own_client:
            client.close()
    if not isinstance(payload, dict):
        raise TypeError(f"unexpected air-quality payload: {type(payload).__name__}")
    return payload


def normalize_payload(
    payload: dict,
    *,
    source: str = "CAMS_via_OpenMeteo",
    availability_lag_hours: float | None = None,
) -> pd.DataFrame:
    """Aggregate hourly AOD/PM values to one row per day and grid point."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    lag = (
        availability_lag_hours
        if availability_lag_hours is not None
        else settings.haze_availability_lag_hours
    )

    def series(name: str) -> pd.Series:
        raw = pd.Series(hourly.get(name) or [], dtype="float64")
        return raw.reindex(range(len(times)))

    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(times, utc=True, errors="coerce"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "aod": series("aerosol_optical_depth"),
            "pm2_5": series("pm2_5"),
            "pm10": series("pm10"),
        }
    )
    frame["date"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    daily = (
        frame.groupby(["date", "latitude", "longitude"], as_index=False)
        .agg(
            aerosol_optical_depth_mean=("aod", "mean"),
            aerosol_optical_depth_max=("aod", "max"),
            pm2_5_mean=("pm2_5", "mean"),
            pm10_mean=("pm10", "mean"),
        )
    )
    daily["available_time"] = pd.to_datetime(daily["date"], utc=True) + pd.to_timedelta(
        lag, unit="h"
    )
    daily["grid_id"] = (
        "CAMS-"
        + daily["longitude"].map(lambda value: f"{value:.2f}")
        + "_"
        + daily["latitude"].map(lambda value: f"{value:.2f}")
    )
    daily["is_fixture"] = False
    daily["source"] = source
    return daily[CANONICAL_COLUMNS]


def default_points(
    bbox: tuple[float, float, float, float] = INDONESIA_BBOX,
    grid: int = 3,
) -> list[tuple[float, float]]:
    """A ``grid`` x ``grid`` lattice of points covering the bbox (CAMS is ~50 km)."""
    if grid < 1:
        raise ValueError("grid must be >= 1")
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = [min_lon + i * (max_lon - min_lon) / (grid - 1) for i in range(grid)] if grid > 1 else [(min_lon + max_lon) / 2]
    lats = [min_lat + i * (max_lat - min_lat) / (grid - 1) for i in range(grid)] if grid > 1 else [(min_lat + max_lat) / 2]
    return [(lat, lon) for lat in lats for lon in lons]


def ingest_grid(
    points: list[tuple[float, float]],
    start: str,
    end: str,
    out_path: Path,
    *,
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
    sleep=time.sleep,
    pause_seconds: float = 1.0,
    max_retries: int = 5,
) -> tuple[pd.DataFrame, Path]:
    """Fetch and normalize daily aerosol/PM values for a list of points.

    Writes Parquet and registers provenance with treatment ``real``. The
    registered notes carry the archive-depth limitation (DEPTH_NOTE).
    """
    frames: list[pd.DataFrame] = []
    for index, (lat, lon) in enumerate(points):
        payload = fetch_point_hourly(
            lat, lon, start, end, client=client, max_retries=max_retries
        )
        frames.append(
            normalize_payload(
                payload,
                availability_lag_hours=settings_obj.haze_availability_lag_hours,
            )
        )
        if index < len(points) - 1 and sleep is not None and pause_seconds > 0:
            sleep(pause_seconds)
    df = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["grid_id", "date"])
        .sort_values(["grid_id", "date"])
        .reset_index(drop=True)
        if frames
        else pd.DataFrame(columns=CANONICAL_COLUMNS)
    )

    from .io import write_parquet
    from .provenance import register_dataset

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(
        df,
        out_path,
        extra_metadata={"dataset": "haze_aerosol", "source": "CAMS via Open-Meteo"},
    )
    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="haze_aerosol::cams_open_meteo",
        name="Haze/aerosol indicators (CAMS via Open-Meteo)",
        source=(
            f"Open-Meteo Air Quality API / CAMS (points={len(points)}, {start}..{end})"
        ),
        license="CC BY 4.0 (Open-Meteo) / Copernicus CAMS attribution",
        treatment="real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["date"].min()) if len(df) else None,
        observation_end=str(df["date"].max()) if len(df) else None,
        notes=(
            f"{DEPTH_NOTE} Daily aggregates treated as available "
            f"{settings_obj.haze_availability_lag_hours:.0f}h after the observation day."
        ),
    )
    return df, out_path
