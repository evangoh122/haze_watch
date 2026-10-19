"""Point-in-time feature building.

Joins hotspot activity and weather observations to plantation polygons using only
data whose ``available_time`` is at or before ``as_of``. This prevents future-data
leakage in every downstream model (project_profile.md section 4).

Spatial rules:

- Hotspot proximity is measured to the **polygon** (0 inside; else distance to the
  nearest boundary point), not to the centroid.
- Weather comes from the **nearest station** to the polygon only; the station id
  and distance are recorded so every value is auditable.
- Haze/aerosol comes from the **nearest CAMS grid point** only. It is a separate
  atmospheric product: AOD/PM are not fire detections and not burned area.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import shapely.wkt

from .config import settings
from .geo import distances_to_geom_km
from .io import read_parquet, write_parquet
from .provenance import derive_treatment, register_dataset

FEATURE_COLUMNS = [
    "polygon_id",
    "as_of",
    "hotspot_count_1d",
    "hotspot_count_7d",
    "hotspot_count_30d",
    "days_since_last_hotspot",
    "nearest_hotspot_km_7d",
    "temp_max_7d_c",
    "precip_sum_7d_mm",
    "humidity_mean_7d_pct",
    "wind_max_7d_ms",
    "weather_station_id",
    "weather_distance_km",
    "aerosol_optical_depth_mean_7d",
    "aerosol_optical_depth_max_7d",
    "pm2_5_mean_7d",
    "pm10_mean_7d",
    "haze_grid_id",
    "haze_distance_km",
]


def _parse_as_of(as_of: str | datetime) -> pd.Timestamp:
    ts = pd.to_datetime(as_of, utc=True)
    return ts


def build_features(
    polygons: pd.DataFrame,
    hotspots: pd.DataFrame,
    weather: pd.DataFrame | None,
    as_of: str | datetime,
    *,
    aerosol: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build leakage-safe features per polygon for a single ``as_of`` timestamp.

    Every input row is filtered on ``available_time <= as_of``; observation time
    windows are then computed relative to ``as_of``.
    """
    as_of_ts = _parse_as_of(as_of)

    hot = hotspots.copy()
    hot["available_time"] = pd.to_datetime(hot["available_time"], utc=True)
    hot["observation_time"] = pd.to_datetime(hot["observation_time"], utc=True)
    hot = hot[hot["available_time"] <= as_of_ts]

    weather_rows: list[dict] = []
    if weather is not None and len(weather):
        wx = weather.copy()
        wx["available_time"] = pd.to_datetime(wx["available_time"], utc=True)
        wx["observation_time"] = pd.to_datetime(wx["observation_time"], utc=True)
        wx = wx[wx["available_time"] <= as_of_ts]
        weather_rows = wx.to_dict("records")
    wx_df = pd.DataFrame(weather_rows)

    aerosol_rows: list[dict] = []
    if aerosol is not None and len(aerosol):
        az = aerosol.copy()
        az["date"] = pd.to_datetime(az["date"], utc=True)
        if "available_time" in az.columns:
            az["available_time"] = pd.to_datetime(az["available_time"], utc=True)
        else:
            az["available_time"] = az["date"] + pd.to_timedelta(
                settings.haze_availability_lag_hours, unit="h"
            )
        if "grid_id" not in az.columns:
            az["grid_id"] = (
                "CAMS-"
                + az["longitude"].map(lambda value: f"{value:.2f}")
                + "_"
                + az["latitude"].map(lambda value: f"{value:.2f}")
            )
        az = az[az["available_time"] <= as_of_ts]
        aerosol_rows = az.to_dict("records")
    az_df = pd.DataFrame(aerosol_rows)

    records: list[dict] = []
    for _, poly in polygons.iterrows():
        geom = shapely.wkt.loads(poly["geometry"])

        # Hotspot proximity measured to the polygon boundary, not the centroid.
        if len(hot):
            dist_km = distances_to_geom_km(
                geom,
                hot["longitude"].to_numpy(),
                hot["latitude"].to_numpy(),
                within_km=settings.exposure_radius_km,
            )
            hot = hot.assign(_dist_km=dist_km)
            near = hot[hot["_dist_km"] <= settings.exposure_radius_km]
        else:
            near = hot

        window_1d = near[near["observation_time"] > as_of_ts - pd.Timedelta(days=1)]
        window_7d = near[near["observation_time"] > as_of_ts - pd.Timedelta(days=7)]
        window_30d = near[near["observation_time"] > as_of_ts - pd.Timedelta(days=30)]

        if len(near):
            days_since = float((as_of_ts - near["observation_time"].max()) / pd.Timedelta(days=1))
            nearest_7d = float(window_7d["_dist_km"].min()) if len(window_7d) else np.nan
        else:
            days_since = np.nan
            nearest_7d = np.nan

        # Weather from the nearest station only (never pooled across stations).
        temp = precip = humidity = wind = np.nan
        station_id = None
        station_km = np.nan
        if len(wx_df):
            stations = wx_df.drop_duplicates("station_id")[["station_id", "latitude", "longitude"]]
            station_dists = distances_to_geom_km(
                geom,
                stations["longitude"].to_numpy(),
                stations["latitude"].to_numpy(),
            )
            if np.isfinite(station_dists).any():
                best = int(np.argmin(station_dists))
                station_id = str(stations.iloc[best]["station_id"])
                station_km = float(station_dists[best])
                if station_km <= settings.weather_max_distance_km:
                    wx_st = wx_df[wx_df["station_id"] == stations.iloc[best]["station_id"]]
                    wx7 = wx_st[wx_st["observation_time"] > as_of_ts - pd.Timedelta(days=7)]
                    if len(wx7):
                        temp = float(wx7["temperature_max_c"].max())
                        precip = float(wx7["precipitation_sum_mm"].sum())
                        humidity = float(wx7["humidity_mean_pct"].mean())
                        wind = float(wx7["wind_max_ms"].max())

        # Haze from the nearest CAMS grid point only, within the defensible radius.
        aod_mean = aod_max = pm25 = pm10 = np.nan
        haze_id = None
        haze_km = np.nan
        if len(az_df):
            points = az_df.drop_duplicates("grid_id")[["grid_id", "latitude", "longitude"]]
            haze_dists = distances_to_geom_km(
                geom,
                points["longitude"].to_numpy(),
                points["latitude"].to_numpy(),
            )
            if np.isfinite(haze_dists).any():
                best_haze = int(np.argmin(haze_dists))
                haze_id = str(points.iloc[best_haze]["grid_id"])
                haze_km = float(haze_dists[best_haze])
                if haze_km <= settings.haze_max_distance_km:
                    az_point = az_df[az_df["grid_id"] == haze_id]
                    az7 = az_point[
                        (az_point["date"] > as_of_ts - pd.Timedelta(days=7))
                        & (az_point["date"] <= as_of_ts)
                    ]
                    if len(az7):
                        aod_mean = float(az7["aerosol_optical_depth_mean"].mean())
                        aod_max = float(az7["aerosol_optical_depth_max"].max())
                        pm25 = float(az7["pm2_5_mean"].mean())
                        pm10 = float(az7["pm10_mean"].mean())

        records.append(
            {
                "polygon_id": poly["polygon_id"],
                "as_of": as_of_ts,
                "hotspot_count_1d": len(window_1d),
                "hotspot_count_7d": len(window_7d),
                "hotspot_count_30d": len(window_30d),
                "days_since_last_hotspot": days_since,
                "nearest_hotspot_km_7d": nearest_7d,
                "temp_max_7d_c": temp,
                "precip_sum_7d_mm": precip,
                "humidity_mean_7d_pct": humidity,
                "wind_max_7d_ms": wind,
                "weather_station_id": station_id,
                "weather_distance_km": station_km,
                "aerosol_optical_depth_mean_7d": aod_mean,
                "aerosol_optical_depth_max_7d": aod_max,
                "pm2_5_mean_7d": pm25,
                "pm10_mean_7d": pm10,
                "haze_grid_id": haze_id,
                "haze_distance_km": haze_km,
            }
        )

    return pd.DataFrame(records, columns=FEATURE_COLUMNS)


def _polygon_treatments(polygons: pd.DataFrame | None) -> list:
    if polygons is None or "treatment" not in polygons.columns:
        return [None]
    return list(polygons["treatment"].unique())


def build_and_save(
    polygons_path,
    hotspots_path,
    weather_path,
    as_of: str | datetime,
    out_path,
    *,
    aerosol_path=None,
    settings_obj=settings,
) -> tuple[pd.DataFrame, object]:
    """Load processed datasets, build features, write Parquet and register provenance."""
    polygons = read_parquet(polygons_path)
    hotspots = read_parquet(hotspots_path)
    weather = read_parquet(weather_path) if weather_path else None
    aerosol = read_parquet(aerosol_path) if aerosol_path else None

    as_of_ts = _parse_as_of(as_of)
    features = build_features(polygons, hotspots, weather, as_of_ts, aerosol=aerosol)

    inputs = [
        bool(hotspots["is_fixture"].any()) if "is_fixture" in hotspots.columns else None,
        *_polygon_treatments(polygons),
    ]
    if aerosol is not None and "is_fixture" in aerosol.columns:
        inputs.insert(0, bool(aerosol["is_fixture"].any()))
    treatment = derive_treatment(*inputs)
    source_parts = [str(hotspots_path), str(weather_path), str(polygons_path)]
    if aerosol_path:
        source_parts.insert(2, str(aerosol_path))
    write_parquet(
        features,
        out_path,
        extra_metadata={"dataset": "environmental_features", "treatment": treatment},
    )

    register_dataset(
        settings_obj.metadata_dir,
        dataset_id=f"environmental_features::{as_of_ts.date().isoformat()}",
        name="Environmental features (point-in-time)",
        source=" + ".join(source_parts),
        license="derived from registered inputs",
        treatment=treatment,
        path=out_path,
        row_count=len(features),
        observation_end=as_of_ts.isoformat(),
        notes="Filter: available_time <= as_of (leakage-safe); weather and haze use the nearest grid point.",
    )
    return features, out_path
