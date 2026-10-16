"""Geospatial exposure calculation with precomputed, anonymized public outputs.

Performs point-in-polygon joins and distance calculations between hotspot
observations and plantation/concession polygons, then writes:

- **internal Parquet**: full exposure table including polygon_id joins.
- **public GeoJSON/GeoParquet**: simplified geometry, anonymized IDs, NO company
  or ownership fields (project_profile.md section 10 re-identification rules).

Hotspot counts are *detections*, not burned area. Every output repeats this caveat.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shapely.geometry
import shapely.wkt

from .config import settings
from .geo import distances_to_geom_km
from .io import read_parquet, write_json, write_parquet
from .provenance import derive_treatment, register_dataset

CAVEAT = (
    "Hotspot counts are satellite fire detections within a buffer, not confirmed "
    "burned area, damage, or evidence of causation or responsibility."
)

EXPOSURE_COLUMNS = [
    "polygon_id",
    "boundary_type",
    "area_ha",
    "centroid_lon",
    "centroid_lat",
    "hotspot_count_in_polygon_30d",
    "hotspot_count_near_30d",
    "nearest_hotspot_km_30d",
    "detection_density_per_1000ha",
    "caveat",
]


def compute_exposure(
    polygons: pd.DataFrame,
    hotspots: pd.DataFrame,
    as_of: str,
    *,
    buffer_km: float | None = None,
) -> pd.DataFrame:
    """Compute per-polygon hotspot exposure for the 30 days before ``as_of``."""
    radius_km = buffer_km if buffer_km is not None else settings.exposure_radius_km
    as_of_ts = pd.to_datetime(as_of, utc=True)

    hot = hotspots.copy()
    hot["observation_time"] = pd.to_datetime(hot["observation_time"], utc=True)
    hot["available_time"] = pd.to_datetime(hot["available_time"], utc=True)
    hot = hot[
        (hot["available_time"] <= as_of_ts)
        & (hot["observation_time"] > as_of_ts - pd.Timedelta(days=30))
    ]

    rows = []
    for _, poly in polygons.iterrows():
        geom = shapely.wkt.loads(poly["geometry"])
        clon, clat = float(poly["centroid_lon"]), float(poly["centroid_lat"])

        if len(hot):
            # Counts within the buffer measured to the polygon boundary...
            dists_near = distances_to_geom_km(
                geom,
                hot["longitude"].to_numpy(),
                hot["latitude"].to_numpy(),
                within_km=radius_km,
            )
            in_poly = int((dists_near == 0.0).sum())
            near_count = int((dists_near <= radius_km).sum())
            # ...and the exact nearest distance, even when beyond the buffer.
            dists_min = distances_to_geom_km(
                geom, hot["longitude"].to_numpy(), hot["latitude"].to_numpy()
            )
            nearest_km = float(dists_min.min())
        else:
            in_poly, near_count, nearest_km = 0, 0, np.nan

        area_ha = float(poly["area_ha"])
        rows.append(
            {
                "polygon_id": poly["polygon_id"],
                "boundary_type": poly["boundary_type"],
                "area_ha": area_ha,
                "centroid_lon": clon,
                "centroid_lat": clat,
                "hotspot_count_in_polygon_30d": in_poly,
                "hotspot_count_near_30d": near_count,
                "nearest_hotspot_km_30d": nearest_km,
                "detection_density_per_1000ha": (in_poly / area_ha * 1000.0) if area_ha > 0 else np.nan,
                "caveat": CAVEAT,
            }
        )

    return pd.DataFrame(rows, columns=EXPOSURE_COLUMNS)


def _round_geojson(obj, ndigits: int):
    """Round coordinates in a GeoJSON geometry mapping (keeps JSON-safe floats)."""
    if isinstance(obj, dict):
        return {key: _round_geojson(value, ndigits) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_geojson(item, ndigits) for item in obj]
    if isinstance(obj, float):
        return round(obj, ndigits)
    return obj


def public_exposure_layer(polygons: pd.DataFrame, exposure: pd.DataFrame, *, simplify_deg: float = 0.01):
    """Build the re-identification-safe public layer (GeoJSON FeatureCollection).

    - Company/ownership/attribution fields are dropped.
    - Geometries are simplified (``simplify_deg``, ~1 km) so exact concession
      boundaries cannot be reconstructed from the public demo.
    """
    merged = polygons.merge(
        exposure[
            [
                "polygon_id",
                "hotspot_count_in_polygon_30d",
                "hotspot_count_near_30d",
            ]
        ],
        on="polygon_id",
        how="inner",
    )
    features = []
    for _, row in merged.iterrows():
        geom = shapely.wkt.loads(row["geometry"]).simplify(simplify_deg, preserve_topology=True)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "polygon_id": row["polygon_id"],
                    "boundary_type": row["boundary_type"],
                    "area_ha_bucket": f"{int(round(row['area_ha'] / 500.0) * 500)}",
                    "hotspot_count_in_polygon_30d": int(row["hotspot_count_in_polygon_30d"]),
                    "hotspot_count_near_30d": int(row["hotspot_count_near_30d"]),
                    "treatment": "real-aggregated" if str(row["treatment"]).startswith("real") else row["treatment"],
                    "caveat": CAVEAT,
                },
                "geometry": _round_geojson(shapely.geometry.mapping(geom), 4),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def run_exposure(
    polygons_path,
    hotspots_path,
    as_of: str,
    out_parquet_path,
    out_public_geojson_path,
    settings_obj=settings,
    buffer_km: float | None = None,
) -> tuple[pd.DataFrame, dict, object]:
    """Full exposure run: compute, persist internal + public outputs, register."""
    polygons = read_parquet(polygons_path)
    hotspots = read_parquet(hotspots_path)

    exposure = compute_exposure(polygons, hotspots, as_of, buffer_km=buffer_km)
    write_parquet(exposure, out_parquet_path, extra_metadata={"dataset": "exposure"})

    public = public_exposure_layer(polygons, exposure)
    out_public_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(public, out_public_geojson_path)

    summary = {
        "as_of": as_of,
        "polygons": len(exposure),
        "hotspots_considered": len(hotspots),
        "polygons_with_detections": int((exposure["hotspot_count_in_polygon_30d"] > 0).sum()),
        "buffer_km": buffer_km or settings.exposure_radius_km,
        "polygon_treatment": sorted({str(t) for t in polygons["treatment"]}),
        "hotspot_treatment": (
            "synthetic-fixture" if bool(hotspots["is_fixture"].any()) else "real"
        ),
        "caveat": CAVEAT,
    }
    if summary["hotspot_treatment"] == "synthetic-fixture":
        summary["warning"] = (
            "INPUT MIX: hotspot detections are SYNTHETIC FIXTURES, not observations. "
            "Exposure numbers are for pipeline testing only and must never be presented "
            "as real fire activity."
        )

    polygon_treatments = (
        list(polygons["treatment"].unique()) if "treatment" in polygons.columns else [None]
    )
    treatment = derive_treatment(
        bool(hotspots["is_fixture"].any()) if "is_fixture" in hotspots.columns else None,
        *polygon_treatments,
    )
    write_json(summary, out_parquet_path.with_suffix(".summary.json"))

    register_dataset(
        settings_obj.metadata_dir,
        dataset_id=f"exposure::{pd.to_datetime(as_of, utc=True).date().isoformat()}",
        name="Geospatial exposure (hotspots x polygons)",
        source=f"{polygons_path} + {hotspots_path}",
        license="derived from registered inputs",
        treatment=treatment,
        path=out_parquet_path,
        row_count=len(exposure),
        observation_end=pd.to_datetime(as_of, utc=True).isoformat(),
        notes=CAVEAT,
    )
    return exposure, summary, out_parquet_path
