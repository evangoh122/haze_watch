"""Tests for polygon-edge distances and the centroid prefilter (exactness rules)."""

import numpy as np
import pytest
import shapely.wkt

from haze_pipelines.geo import (
    distances_to_geom_km,
    geom_circumradius_km,
    haversine_km,
    point_to_geom_km,
)

# 0.2-degree square centered at (113.0, -2.0): lon 112.9..113.1, lat -2.1..-1.9
SQUARE = shapely.wkt.loads(
    "POLYGON ((112.9 -2.1, 113.1 -2.1, 113.1 -1.9, 112.9 -1.9, 112.9 -2.1))"
)


def test_point_inside_polygon_is_zero_distance():
    assert point_to_geom_km(SQUARE, 113.0, -2.0) == 0.0
    assert point_to_geom_km(SQUARE, 112.9, -2.1) == 0.0  # boundary counts as inside


def test_distance_is_to_edge_not_centroid():
    # 0.25 deg east of the eastern edge (lon 113.1) at lat -2.0.
    d = point_to_geom_km(SQUARE, 113.35, -2.0)
    expected = haversine_km(-2.0, 113.1, -2.0, 113.35)  # to the nearest edge
    assert d == pytest.approx(expected, abs=0.05)
    # Centroid distance would be roughly double for this elongated case.
    assert d < haversine_km(-2.0, 113.0, -2.0, 113.35)


def test_elongated_polygon_uses_edge_distance():
    # 2.2-degree-wide sliver: centroid is far from the eastern edge.
    sliver = shapely.wkt.loads(
        "POLYGON ((112.9 -2.05, 115.1 -2.05, 115.1 -1.95, 112.9 -1.95, 112.9 -2.05))"
    )
    point_lon, point_lat = 115.15, -2.0
    d = point_to_geom_km(sliver, point_lon, point_lat)
    expected_edge = haversine_km(-2.0, 115.1, -2.0, 115.15)
    assert d == pytest.approx(expected_edge, abs=0.05)
    # The centroid distance is >100 km away: this is the bug being prevented.
    centroid_d = haversine_km(-2.0, 114.0, point_lat, point_lon)
    assert centroid_d > 100


def test_distances_mask_is_exact_within_radius():
    lons = [113.0, 113.35, 114.5]
    lats = [-2.0, -2.0, -2.0]
    dists = distances_to_geom_km(SQUARE, lons, lats, within_km=30.0)
    assert dists[0] == 0.0
    assert dists[1] == pytest.approx(haversine_km(-2.0, 113.1, -2.0, 113.35), abs=0.05)
    # Far point is outside the radius: masked as inf, never counted.
    assert np.isinf(dists[2])
    assert (dists <= 30.0).sum() == 2
    # Edge semantics: the ~27.8 km point is excluded from a 25 km buffer.
    dists_25 = distances_to_geom_km(SQUARE, lons, lats, within_km=25.0)
    assert (dists_25 <= 25.0).sum() == 1


def test_nearest_search_finds_exact_min_beyond_radius():
    lons = [113.35, 114.5]
    lats = [-2.0, -2.0]
    dists = distances_to_geom_km(SQUARE, lons, lats)  # within_km=None: nearest search
    assert dists.min() == pytest.approx(haversine_km(-2.0, 113.1, -2.0, 113.35), abs=0.05)


def test_empty_inputs_return_empty_array():
    out = distances_to_geom_km(SQUARE, [], [])
    assert out.size == 0


def test_circumradius_bounds_all_points():
    radius = geom_circumradius_km(SQUARE)
    for lon, lat in [(112.9, -2.1), (113.1, -1.9), (113.0, -2.0)]:
        assert haversine_km(-2.0, 113.0, lat, lon) <= radius + 1e-6
