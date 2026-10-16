"""GeoParquet (OGC) helpers for the durable history store on Hugging Face.

Writes Parquet files with a WKB ``geometry`` column and the GeoParquet ``geo``
schema metadata, so DuckDB spatial, GeoPandas and QGIS read them directly.
Coordinates are WGS84 lon/lat (GeoParquet's default CRS is OGC:CRS84), which is
the FIRMS detection geometry - public point data, no restricted concession
geometry ever passes through here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

GEO_METADATA_VERSION = "1.0.0"
PRIMARY_COLUMN = "geometry"


def points_to_geoparquet(
    df: pd.DataFrame,
    out_path: Path,
    *,
    lon: str = "longitude",
    lat: str = "latitude",
) -> Path:
    """Write ``df`` with a WKB Point ``geometry`` column + GeoParquet metadata.

    Rows with missing coordinates get a null geometry (GeoParquet allows nulls).
    ``lon``/``lat`` columns are kept as-is for consumers that prefer plain
    coordinates. CRS is omitted per spec: GeoParquet defaults to OGC:CRS84.
    """
    from shapely.geometry import Point

    out = df.copy()
    out[PRIMARY_COLUMN] = [
        None if pd.isna(x) or pd.isna(y) else Point(float(x), float(y)).wkb
        for x, y in zip(df[lon], df[lat])
    ]
    table = pa.Table.from_pandas(out, preserve_index=False)
    geo = {
        "version": GEO_METADATA_VERSION,
        "primary_column": PRIMARY_COLUMN,
        "columns": {
            PRIMARY_COLUMN: {
                "encoding": "WKB",
                "geometry_types": ["Point"],
            }
        },
    }
    metadata = dict(table.schema.metadata or {})
    metadata[b"geo"] = json.dumps(geo).encode("utf-8")
    table = table.replace_schema_metadata(metadata)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_path)
    return out_path


def merge_hotspots(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Merge newly fetched detections into a year's history, deduping rows.

    Deduplication is on ``hotspot_id`` (a stable hash of source/lat/lon/time),
    so re-running a window or overlapping pulls never double-counts. A
    previously stored ``geometry`` column is dropped and regenerated on write.
    """
    frames = []
    for frame in (existing, new):
        if frame is None or not len(frame):
            continue
        frames.append(frame.drop(columns=[PRIMARY_COLUMN], errors="ignore"))
    if not frames:
        return new.iloc[0:0]
    merged = pd.concat(frames, ignore_index=True)
    return merged.drop_duplicates(subset=["hotspot_id"]).reset_index(drop=True)
