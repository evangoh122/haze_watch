"""Unit tests: GeoParquet writing and history merging."""

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from haze_pipelines.geoparquet import merge_hotspots, points_to_geoparquet


def _hotspots() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hotspot_id": ["a", "b", "c"],
            "latitude": [-2.21, -1.10, float("nan")],
            "longitude": [113.92, 112.30, 114.0],
            "observation_time": pd.to_datetime(
                ["2015-09-01T04:30Z", "2015-09-01T18:30Z", "2015-09-02T04:30Z"], utc=True
            ),
        }
    )


def test_points_to_geoparquet_writes_geo_metadata_and_wkb(tmp_path: Path):
    from shapely import wkb

    out = tmp_path / "year=2015.parquet"
    points_to_geoparquet(_hotspots(), out)

    table = pq.read_table(out)
    geo = json_loads(table.schema.metadata[b"geo"])
    assert geo["primary_column"] == "geometry"
    assert geo["columns"]["geometry"]["encoding"] == "WKB"

    df = table.to_pandas()
    first = wkb.loads(df.loc[0, "geometry"])
    assert first.x == pytest.approx(113.92) and first.y == pytest.approx(-2.21)
    assert df.loc[2, "geometry"] is None  # missing coords -> null geometry
    assert df["longitude"].tolist()[0] == pytest.approx(113.92)  # coords kept


def test_merge_hotspots_dedups_on_hotspot_id():
    existing = _hotspots().iloc[:2]
    new = _hotspots().iloc[1:]  # 'b' overlaps

    merged = merge_hotspots(existing, new)
    assert sorted(merged["hotspot_id"]) == ["a", "b", "c"]


def test_merge_hotspots_regenerates_geometry():
    with_geometry = _hotspots().iloc[:1].assign(geometry=b"\x01\x02")
    merged = merge_hotspots(with_geometry, _hotspots().iloc[1:])
    assert "geometry" not in merged.columns


def test_merge_hotspots_handles_empty_sides():
    empty = _hotspots().iloc[0:0]
    assert len(merge_hotspots(None, empty)) == 0
    assert len(merge_hotspots(None, _hotspots())) == 3


def json_loads(raw: bytes) -> dict:
    import json

    return json.loads(raw.decode("utf-8"))
