"""Parquet and JSON I/O with CRS/provenance metadata.

Geometry columns are stored as WKT text in a column named ``geometry`` and the
Parquet key-value metadata (custom ``haze_geo`` key) records the CRS and
encoding. Note this is a lightweight convention, NOT the GeoParquet spec:
GeoPandas will see a plain WKT string column, not a geometry column. Convert
with ``geopandas.GeoSeries.from_wkt`` if needed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

GEO_METADATA_KEY = b"haze_geo"

DEFAULT_CRS = "EPSG:4326"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_parquet(
    df: pd.DataFrame,
    path: Path,
    *,
    geometry_column: str | None = None,
    crs: str = DEFAULT_CRS,
    extra_metadata: dict[str, str] | None = None,
) -> Path:
    """Write a DataFrame to Parquet, recording CRS/geometry metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)

    metadata = dict(table.schema.metadata or {})
    geo = {"crs": crs}
    if geometry_column is not None:
        geo["geometry_column"] = geometry_column
        geo["encoding"] = "WKT"
    if extra_metadata:
        geo.update(extra_metadata)
    metadata[GEO_METADATA_KEY] = json.dumps(geo).encode("utf-8")

    pq.write_table(table.replace_schema_metadata(metadata), path)
    return path


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def read_geo_metadata(path: Path) -> dict[str, Any]:
    schema = pq.read_schema(path)
    raw = (schema.metadata or {}).get(GEO_METADATA_KEY)
    return json.loads(raw.decode("utf-8")) if raw else {}


def write_json(obj: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
