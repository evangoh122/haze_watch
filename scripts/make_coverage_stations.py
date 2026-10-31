"""Pick a small ERA5 coverage set from concession geometry.

A regular grid is simple but wasteful: ERA5 can be queried at any point, so a
handful of well-placed points can cover every concession inside the feature
distance limit with far fewer API calls. This script runs k-means on the
polygon representative points, picks the best of several seeds by the worst-case
nearest-point distance, and writes the station CSV consumed by
``haze-pipelines ingest-weather --stations``.

Usage:
    uv run python scripts/make_coverage_stations.py \
        --polygons data/processed/plantation_polygons.parquet \
        --k 5 --out data/raw/weather/era5_coverage_5.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import shapely.wkt
from haze_pipelines.geo import haversine_km


def coverage_points(
    lat: np.ndarray,
    lon: np.ndarray,
    k: int,
    *,
    seeds: int = 20,
    max_iter: int = 200,
) -> tuple[np.ndarray, float]:
    """Return ``k`` (lat, lon) centers and the worst-case nearest distance in km."""
    points = np.column_stack([lat, lon])

    def nearest(centers: np.ndarray) -> np.ndarray:
        return haversine_km(
            points[:, 0, None],
            points[:, 1, None],
            centers[None, :, 0],
            centers[None, :, 1],
        ).min(axis=1)

    best_centers: np.ndarray | None = None
    best_worst = float("inf")
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        centers = points[rng.choice(len(points), k, replace=False)]
        for _ in range(max_iter):
            distances = haversine_km(
                points[:, 0, None],
                points[:, 1, None],
                centers[None, :, 0],
                centers[None, :, 1],
            )
            labels = distances.argmin(axis=1)
            updated = np.array(
                [
                    points[labels == index].mean(axis=0)
                    if (labels == index).any()
                    else centers[index]
                    for index in range(k)
                ]
            )
            if np.allclose(updated, centers, atol=1e-7):
                break
            centers = updated
        worst = float(nearest(centers).max())
        if worst < best_worst:
            best_centers, best_worst = centers, worst
    if best_centers is None:
        raise RuntimeError("k-means produced no centers")
    return best_centers, best_worst


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polygons", required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args()

    if args.k < 1:
        parser.error("--k must be >= 1")

    frame = pd.read_parquet(args.polygons)
    points = [shapely.wkt.loads(geometry).representative_point() for geometry in frame["geometry"]]
    lat = np.array([point.y for point in points])
    lon = np.array([point.x for point in points])

    centers, worst = coverage_points(lat, lon, args.k, seeds=args.seeds)
    stations = pd.DataFrame(
        {
            "station_id": [f"ERA5-COV-{index + 1}" for index in range(args.k)],
            "label": [f"ERA5 coverage point {index + 1}" for index in range(args.k)],
            "latitude": centers[:, 0],
            "longitude": centers[:, 1],
        }
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stations.to_csv(out, index=False)
    print(f"{args.k} coverage points -> {out}")
    print(f"worst-case nearest distance: {worst:.1f} km")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
