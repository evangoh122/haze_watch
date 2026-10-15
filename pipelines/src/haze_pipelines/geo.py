"""Geometry helpers.

All coordinates are WGS84 (EPSG:4326) lon/lat degrees. Distances use the great
circle (haversine) in kilometres. Areas are geodesic (pyproj) where available and
fall back to a documented local-scale approximation otherwise.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points

EARTH_RADIUS_KM = 6371.0088

# Indonesia bounding box: min_lon, min_lat, max_lon, max_lat.
INDONESIA_BBOX: tuple[float, float, float, float] = (94.0, -11.5, 141.5, 6.5)


def haversine_km(
    lat1: ArrayLike, lon1: ArrayLike, lat2: ArrayLike, lon2: ArrayLike
) -> NDArray[np.float64] | float:
    """Great-circle distance in km. Broadcasts over numpy-compatible inputs."""
    rlat1 = np.radians(np.asarray(lat1, dtype=float))
    rlon1 = np.radians(np.asarray(lon1, dtype=float))
    rlat2 = np.radians(np.asarray(lat2, dtype=float))
    rlon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2.0) ** 2
    dist = 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return float(dist) if np.ndim(dist) == 0 else dist


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def centroid_lon_lat(geom: BaseGeometry) -> tuple[float, float]:
    c = geom.centroid
    return float(c.x), float(c.y)


def approx_area_ha(geom: BaseGeometry) -> float:
    """Approximate polygon area in hectares (fallback when no source attribute).

    Uses a local equirectangular scale at the centroid latitude. Documented as an
    approximation; prefer the source dataset's own area attribute where present.
    """
    try:
        from pyproj import Geod

        area_m2, _ = Geod(ellps="WGS84").geometry_area_perimeter(geom)
        return abs(area_m2) / 10_000.0
    except Exception:  # noqa: BLE001 - pyproj absent or geometry rejected; documented fallback
        lat = centroid_lon_lat(geom)[1]
        km2 = geom.area * (111.32 * np.cos(np.radians(lat))) * 110.57
        return float(km2) * 100.0


def point_to_geom_km(geom: BaseGeometry, lon: float, lat: float) -> float:
    """Distance from a point to a polygon in km (0.0 when inside or on the boundary).

    Distance is measured to the nearest *boundary* point, not to the centroid -
    correct for large or elongated concessions.
    """
    point = Point(lon, lat)
    if geom.intersects(point):
        return 0.0
    boundary = geom.boundary if not geom.boundary.is_empty else geom
    near = nearest_points(boundary, point)[0]
    return float(haversine_km(lat, lon, near.y, near.x))


def geom_circumradius_km(geom: BaseGeometry) -> float:
    """Upper bound (km) on the distance from the centroid to any point of a geom."""
    lon, lat = centroid_lon_lat(geom)
    minx, miny, maxx, maxy = geom.bounds
    corners = [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]
    return float(max(haversine_km(lat, lon, clat, clon) for clon, clat in corners))


def distances_to_geom_km(
    geom: BaseGeometry,
    lons: ArrayLike,
    lats: ArrayLike,
    *,
    within_km: float | None = None,
) -> NDArray[np.float64]:
    """Distance from each point to a polygon (0.0 inside/on boundary).

    Exact for every point whose true distance is ``<= within_km``, and the
    returned minimum is always the exact nearest distance. Points proven
    irrelevant by a centroid prefilter are ``np.inf``, so ``(d <= r)`` masks and
    ``d.min()`` stay correct.

    Prefilter guarantee: with ``R`` = centroid circumradius and ``d0`` = distance
    to the centroid, ``|d0 - d| <= R``.  With ``within_km`` set, candidates are
    ``d0 <= within_km + R`` (excluded points satisfy ``d > within_km``); for a
    nearest search (``within_km=None``) candidates are ``d0 <= min(d0) + 2R``
    (excluded points cannot be the nearest).
    """
    lon_arr = np.asarray(lons, dtype=float)
    lat_arr = np.asarray(lats, dtype=float)
    out = np.full(lon_arr.shape, np.inf, dtype=float)
    if lon_arr.size == 0:
        return out

    cx, cy = centroid_lon_lat(geom)
    d0 = np.atleast_1d(np.asarray(haversine_km(lat_arr, lon_arr, cy, cx), dtype=float))
    radius = geom_circumradius_km(geom)

    if within_km is not None:
        cutoff = float(within_km) + radius
    else:
        cutoff = float(d0.min()) + 2.0 * radius

    for idx in np.where(d0 <= cutoff)[0]:
        out[idx] = point_to_geom_km(geom, float(lon_arr[idx]), float(lat_arr[idx]))
    return out
