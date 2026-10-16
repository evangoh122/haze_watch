"""Unit tests: exposure calculation and anonymized public layer."""

import math

import pandas as pd
import shapely.wkt
from shapely.geometry import shape

from haze_pipelines.fixtures import fixture_hotspots, fixture_polygon_features
from haze_pipelines.ingest_firms import normalize_firms
from haze_pipelines.ingest_polygons import (
    ATTRIBUTION_COLUMNS,
    anonymized_id,
    normalize_polygons,
)
from haze_pipelines.run_exposure import compute_exposure, public_exposure_layer

POLYGONS = normalize_polygons(
    fixture_polygon_features(),
    source_dataset="FIXTURE",
    boundary_type="concession",
    license="test",
    vintage="2026",
    treatment="synthetic-fixture",
)[0]


def _hotspots():
    raw = fixture_hotspots(n=10, start=pd.Timestamp("2026-01-01", tz="UTC").to_pydatetime())
    return normalize_firms(raw, source="FIXTURE", available_lag_hours=1.0, is_fixture=True)


def test_exposure_counts_and_distances():
    exposure = compute_exposure(POLYGONS, _hotspots(), "2026-02-01T00:00:00Z", buffer_km=25.0)
    exposure = exposure.set_index("polygon_id")

    assert set(exposure.index) == set(POLYGONS["polygon_id"])
    # Fixture hotspots cluster at (113.0, -2.0), inside polygon A.
    poly_a = anonymized_id("FIXTURE", "fixture-a")
    assert exposure.loc[poly_a, "hotspot_count_in_polygon_30d"] > 0

    # Anything inside a polygon is also within the centroid buffer for these sizes.
    assert (exposure["hotspot_count_near_30d"] >= exposure["hotspot_count_in_polygon_30d"]).all()
    assert (exposure["detection_density_per_1000ha"] >= 0).all()
    assert exposure["nearest_hotspot_km_30d"].notna().all()


def _wiggly_polygons():
    """A dense, noisy polygon where simplification provably removes vertices."""
    cx, cy, r = 113.0, -2.0, 0.2
    ring = [
        (
            cx + (r + 0.003 * math.sin(8 * a)) * math.cos(a),
            cy + (r + 0.003 * math.sin(8 * a)) * math.sin(a),
        )
        for a in [i / 64 * 2 * math.pi for i in range(65)]
    ]
    feature = {
        "type": "Feature",
        "properties": {
            "gfwid": "wiggly-1",
            "name": "Fixture Wiggly",
            "company": "Fixture Co W",
            "group_comp": "Fixture Group",
            "area_ha": 30000,
        },
        "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in ring]]},
    }
    return normalize_polygons(
        [feature],
        source_dataset="FIXTURE",
        boundary_type="concession",
        license="test",
        vintage="2026",
        treatment="synthetic-fixture",
    )[0]


def test_public_layer_drops_attribution_and_simplifies():
    polygons = _wiggly_polygons()
    exposure = compute_exposure(polygons, _hotspots(), "2026-02-01T00:00:00Z")
    public = public_exposure_layer(polygons, exposure)

    assert public["type"] == "FeatureCollection"
    assert len(public["features"]) == 1
    props = public["features"][0]["properties"]
    for col in ATTRIBUTION_COLUMNS + ["company", "group_comp", "name", "po_hgu"]:
        assert col not in props
    assert props["polygon_id"].startswith("poly_")
    assert "not confirmed" in props["caveat"]

    source_geom = shapely.wkt.loads(polygons.iloc[0]["geometry"])
    public_geom = shape(public["features"][0]["geometry"])
    assert public_geom.is_valid
    # Coordinates are rounded to 4 decimals (~11 m): exact boundary not reproducible.
    coords = public["features"][0]["geometry"]["coordinates"]
    flat = [c for ring in coords for pt in ring for c in pt]
    assert all(len(str(c).split(".")[-1]) <= 4 for c in flat)
    # Exact boundary is not reproduced: simplification removes vertices.
    assert public_geom.exterior.coords.__len__() < source_geom.exterior.coords.__len__()


def test_caveat_present_on_every_row():
    exposure = compute_exposure(POLYGONS, _hotspots(), "2026-02-01T00:00:00Z")
    assert exposure["caveat"].str.contains("not confirmed").all()


def test_exposure_uses_polygon_edge_distance():
    """Regression: distances were centroid-based, misleading for large concessions."""
    elongated = pd.DataFrame(
        [
            {
                "polygon_id": "poly-sliver",
                "boundary_type": "concession",
                "source_dataset": "FIXTURE",
                "source_feature_id": "sliver",
                "company_attribution": None,
                "group_attribution": None,
                "attribution_confidence": "unverified",
                "area_ha": 40000.0,
                "area_source": "source_attribute",
                "vintage": "2026",
                "license": "test",
                "treatment": "synthetic-fixture",
                "centroid_lon": 114.0,
                "centroid_lat": -2.0,
                # 2.2-degree-wide sliver: its eastern edge is near lon 115.1.
                "geometry": "POLYGON ((112.9 -2.05, 115.1 -2.05, 115.1 -1.95, 112.9 -1.95, 112.9 -2.05))",
            }
        ]
    )
    # One hotspot just inside the eastern edge, one 5 km beyond it, one far away.
    hotspots = pd.DataFrame(
        [
            {
                "hotspot_id": "h-inside",
                "source": "FIXTURE",
                "satellite": "FIXTURE",
                "latitude": -2.0,
                "longitude": 115.05,
                "observation_time": pd.Timestamp("2026-01-15", tz="UTC"),
                "available_time": pd.Timestamp("2026-01-15", tz="UTC"),
                "brightness_k": 320.0,
                "frp_mw": 5.0,
                "confidence_pct": 70.0,
                "daynight": "D",
                "is_fixture": True,
            },
            {
                "hotspot_id": "h-near",
                "source": "FIXTURE",
                "satellite": "FIXTURE",
                "latitude": -2.0,
                "longitude": 115.15,
                "observation_time": pd.Timestamp("2026-01-15", tz="UTC"),
                "available_time": pd.Timestamp("2026-01-15", tz="UTC"),
                "brightness_k": 320.0,
                "frp_mw": 5.0,
                "confidence_pct": 70.0,
                "daynight": "D",
                "is_fixture": True,
            },
        ]
    )
    exposure = compute_exposure(elongated, hotspots, "2026-02-01T00:00:00Z", buffer_km=25.0).iloc[0]

    assert exposure["hotspot_count_in_polygon_30d"] == 1  # h-inside
    # h-near is ~5.5 km from the edge but >120 km from the centroid: a centroid
    # implementation would have missed it in the 25 km buffer.
    assert exposure["hotspot_count_near_30d"] == 2
    assert exposure["nearest_hotspot_km_30d"] == 0.0
