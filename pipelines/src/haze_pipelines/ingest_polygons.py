"""Plantation / concession polygon ingestion.

Supports two intake paths:

1. **BNPB ArcGIS REST service** (``Global_forest_watch2`` layer, GFW oil palm
   concessions) with pagination, retries, deduplication and geometry validation.
2. **Local GeoJSON / GeoPackage files** downloaded by the user from Global Forest
   Watch, MapBiomas or other licensed sources.

Governance (project_profile.md sections 3 and 10):

- Public visibility of a GIS service does **not** grant permission to redistribute
  or commercially reuse Indonesian concession geometries. RSPO explicitly excludes
  Indonesian concession boundaries from its downloadable packages for this reason.
  Verify the licence of every source before any public release.
- Fetching the BNPB layer requires the explicit ``confirm_license`` flag.
- Source attributes such as ``company`` / ``group_comp`` are recorded as
  **attribution fields with confidence "unverified"**; they are excluded from
  public exports by :mod:`haze_pipelines.run_exposure`.
- ``boundary_type`` distinguishes *concession* boundaries (land allocated for
  development) from *plantation* boundaries (land actually planted).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import shapely.wkt
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from .config import Settings, settings
from .geo import approx_area_ha, centroid_lon_lat
from .io import write_parquet
from .provenance import register_dataset
from .quality import QualityReport, validate_polygons

BNPB_QUERY_URL = (
    "https://gis.bnpb.go.id/server/rest/services/InAWARE/Global_forest_watch2/MapServer/6/query"
)

# WRI Global Forest Watch "Indonesia oil palm concessions" layer (schema-identical
# to the BNPB mirror). Kept as a first-class source even when temporarily broken.
GFW_QUERY_URL = (
    "https://gis-gfw.wri.org/arcgis/rest/services/country_data/asia/MapServer/2/query"
)

# Same service, layer 10: "Indonesia Peat Lands" (peatland features, spec section 3).
GFW_PEATLAND_QUERY_URL = (
    "https://gis-gfw.wri.org/arcgis/rest/services/country_data/asia/MapServer/10/query"
)

SOURCE_QUERY_URLS = {
    "bnpb": BNPB_QUERY_URL,
    "gfw": GFW_QUERY_URL,
    "gfw-peatlands": GFW_PEATLAND_QUERY_URL,
}

LICENSE_WARNING = (
    "Public GIS visibility does not imply redistribution rights. Verify licence "
    "terms (GFW custom licence / Indonesian restrictions) before publishing geometry."
)

BOUNDARY_TYPES = ("concession", "plantation", "mill", "other")

CANONICAL_COLUMNS = [
    "polygon_id",
    "boundary_type",
    "source_dataset",
    "source_feature_id",
    "company_attribution",
    "group_attribution",
    "attribution_confidence",
    "area_ha",
    "area_source",
    "vintage",
    "license",
    "treatment",
    "centroid_lon",
    "centroid_lat",
    "geometry",
]

# Columns that must never appear in public exports.
ATTRIBUTION_COLUMNS = ["company_attribution", "group_attribution", "source_feature_id"]


def anonymized_id(source_dataset: str, source_feature_id: str) -> str:
    """Stable, non-semantic public identifier for a polygon."""
    raw = f"{source_dataset}::{source_feature_id}"
    return "poly_" + hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def fetch_arcgis_features(
    query_url: str,
    *,
    client: httpx.Client | None = None,
    page_size: int = 200,
    max_records: int | None = None,
    confirm_license: bool = False,
    max_retries: int = 3,
    sleep=time.sleep,
) -> list[dict[str, Any]]:
    """Fetch GeoJSON features from any ArcGIS MapServer layer query endpoint.

    Handles pagination (``resultOffset``), retries with backoff and de-duplication
    on ``gfwid``/``objectid``. Raises unless ``confirm_license`` is True, because
    redistribution of Indonesian concession geometry may be legally restricted.
    """
    if not confirm_license:
        raise PermissionError(
            "Refusing to download concession geometry without confirm_license=True. "
            + LICENSE_WARNING
        )

    own_client = client is None
    client = client or httpx.Client(timeout=60.0)
    collected: dict[str, dict[str, Any]] = {}
    offset = 0
    try:
        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "f": "geojson",
            }
            data: dict[str, Any] | None = None
            for attempt in range(max_retries):
                try:
                    response = client.get(query_url, params=params, timeout=60.0)
                    response.raise_for_status()
                    payload: Any = response.json()
                    if isinstance(payload, dict) and "error" in payload:
                        # ArcGIS application-level error: retry, then fail clearly.
                        if attempt == max_retries - 1:
                            raise RuntimeError(
                                f"ArcGIS query failed for {query_url}: {payload['error']}. "
                                "If this persists, try the BNPB mirror "
                                "(fetch-concessions --source bnpb) or download the "
                                "dataset manually from data.globalforestwatch.org."
                            )
                    else:
                        data = payload
                        break
                except (httpx.TransportError, httpx.HTTPStatusError):
                    if attempt == max_retries - 1:
                        raise
                sleep(2**attempt)

            batch = (data or {}).get("features", [])
            for feature in batch:
                props = feature.get("properties") or {}
                fid = str(props.get("gfwid") or props.get("objectid") or "")
                key = fid or hashlib.sha1(str(feature).encode("utf-8"), usedforsecurity=False).hexdigest()
                collected[key] = feature

            offset += len(batch)
            if len(batch) < page_size:
                break
            if max_records is not None and len(collected) >= max_records:
                break
    finally:
        if own_client:
            client.close()

    features = list(collected.values())
    return features[:max_records] if max_records else features


def fetch_bnpb_features(**kwargs) -> list[dict[str, Any]]:
    """Fetch oil palm concession features from the BNPB ArcGIS mirror (GFW source)."""
    return fetch_arcgis_features(BNPB_QUERY_URL, **kwargs)


def fetch_gfw_features(**kwargs) -> list[dict[str, Any]]:
    """Fetch oil palm concession features from the WRI Global Forest Watch service."""
    return fetch_arcgis_features(GFW_QUERY_URL, **kwargs)


def normalize_polygons(
    features: Iterable[dict[str, Any]],
    *,
    source_dataset: str,
    boundary_type: str,
    license: str,
    vintage: str | None,
    treatment: str = "real-restricted",
    name_field: str = "name",
    company_field: str = "company",
    group_field: str = "group_comp",
    area_field: str = "area_ha",
    id_field: str = "gfwid",
    make_valid: bool = True,
) -> tuple[pd.DataFrame, QualityReport]:
    """Normalize GeoJSON-like features to the canonical polygon schema.

    Invalid geometries are repaired with ``make_valid`` when possible and reported.
    Company/group names are stored as *unverified attribution* fields; they are
    dropped from every public export.
    """
    if boundary_type not in BOUNDARY_TYPES:
        raise ValueError(f"boundary_type must be one of {BOUNDARY_TYPES}")

    rows: list[dict[str, Any]] = []
    repaired = 0
    skipped = 0

    for feature in features:
        geometry: BaseGeometry | None = None
        try:
            geom_json = feature.get("geometry")
            geometry = shape(geom_json) if geom_json else shapely.wkt.loads(feature.get("wkt", ""))
        except Exception:  # noqa: BLE001 - malformed external GeoJSON must be skipped, not crash ingest
            skipped += 1
            continue

        if geometry.is_empty:
            skipped += 1
            continue
        if not geometry.is_valid:
            if make_valid:
                geometry = geometry.buffer(0)
                repaired += 1
            else:
                skipped += 1
                continue
        if geometry.is_empty or geometry.geom_type not in ("Polygon", "MultiPolygon"):
            skipped += 1
            continue

        props = feature.get("properties") or feature.get("attributes") or {}
        source_feature_id = str(props.get(id_field) or props.get("objectid") or "")
        centroid_lon, centroid_lat = centroid_lon_lat(geometry)

        area_attr = props.get(area_field)
        if area_attr is not None and pd.notna(area_attr) and float(area_attr) > 0:
            area_ha, area_source = float(area_attr), "source_attribute"
        else:
            area_ha, area_source = approx_area_ha(geometry), "computed_approximation"

        rows.append(
            {
                "polygon_id": anonymized_id(source_dataset, source_feature_id or geometry.wkt),
                "boundary_type": boundary_type,
                "source_dataset": source_dataset,
                "source_feature_id": source_feature_id,
                "company_attribution": str(props.get(company_field) or "") or None,
                "group_attribution": str(props.get(group_field) or "") or None,
                "attribution_confidence": "unverified",
                "area_ha": area_ha,
                "area_source": area_source,
                "vintage": vintage,
                "license": license,
                "treatment": treatment,
                "centroid_lon": centroid_lon,
                "centroid_lat": centroid_lat,
                "geometry": geometry.wkt,
            }
        )

    df = pd.DataFrame(rows, columns=CANONICAL_COLUMNS)
    report = validate_polygons(df, dataset=f"plantation_polygons[{source_dataset}]")
    report.add(
        "geometry_repair_rate",
        repaired <= max(1, 0.05 * (len(rows) + skipped)),
        f"{repaired} geometries repaired via buffer(0), {skipped} skipped",
        severity="warning",
        count=repaired,
    )
    return df, report


def normalize_local_geojson(
    path: Path,
    *,
    source_dataset: str,
    boundary_type: str,
    license: str,
    vintage: str | None,
    treatment: str = "real-restricted",
) -> tuple[pd.DataFrame, QualityReport]:
    """Normalize a local GeoJSON FeatureCollection (e.g. GFW download)."""
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", [])
    return normalize_polygons(
        features,
        source_dataset=source_dataset,
        boundary_type=boundary_type,
        license=license,
        vintage=vintage,
        treatment=treatment,
    )


def ingest_polygon_file(
    input_path: Path,
    out_path: Path,
    *,
    source_dataset: str,
    boundary_type: str,
    license: str,
    vintage: str | None,
    treatment: str = "real-restricted",
    settings_obj: Settings = settings,
) -> tuple[pd.DataFrame, QualityReport, Path]:
    """Normalize a local polygon file, write Parquet and register provenance."""
    df, report = normalize_local_geojson(
        input_path,
        source_dataset=source_dataset,
        boundary_type=boundary_type,
        license=license,
        vintage=vintage,
        treatment=treatment,
    )
    if not report.passed:
        raise ValueError(f"polygon quality checks failed: {[c.name for c in report.errors]}")

    write_parquet(
        df,
        out_path,
        geometry_column="geometry",
        extra_metadata={"dataset": "plantation_polygons", "treatment": treatment},
    )
    register_dataset(
        settings_obj.metadata_dir,
        dataset_id=f"plantation_polygons::{source_dataset}",
        name=f"Plantation/concession polygons ({source_dataset})",
        source=str(input_path),
        license=license,
        treatment=treatment,
        path=out_path,
        row_count=len(df),
        vintage=vintage,
        notes=f"boundary_type={boundary_type}; attribution fields unverified. {LICENSE_WARNING}",
    )
    return df, report, out_path
