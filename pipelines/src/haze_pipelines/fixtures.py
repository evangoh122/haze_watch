"""Clearly-labeled synthetic fixtures for tests and offline development.

NEVER present fixture output as environmental observation. Fixture hotspot rows
carry ``is_fixture=True`` and fixture polygons are registered with treatment
``synthetic-fixture``. Real ingestion paths (``ingest_firms``, ``ingest_polygons``)
must not call these functions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

FIXTURE_NOTICE = "SYNTHETIC FIXTURE - not an environmental observation"


def fixture_hotspots(
    *,
    n: int = 12,
    center: tuple[float, float] = (113.0, -2.0),
    start: datetime | None = None,
    seed: int = 7,
) -> pd.DataFrame:
    """Deterministic FIRMS-shaped hotspot rows near ``center`` (lon, lat)."""
    start = start or datetime(2026, 1, 1, tzinfo=UTC)
    lon0, lat0 = center

    rows = []
    for i in range(n):
        obs = start + timedelta(hours=6 * i)
        rows.append(
            {
                # Real FIRMS export column names (acq_date / acq_time as HHMM int).
                "latitude": round(lat0 + ((i * 37) % 11 - 5) * 0.02, 5),
                "longitude": round(lon0 + ((i * 53) % 13 - 6) * 0.02, 5),
                "brightness": 320.0 + (i % 5) * 12.5,
                "scan": 1.0,
                "track": 1.0,
                "acq_date": obs.strftime("%Y-%m-%d"),
                "acq_time": int(obs.strftime("%H%M")),
                "satellite": "FIXTURE",
                "confidence": 60 + (i % 3) * 10,
                "version": "synthetic_fixture_0",
                "bright_t31": 295.0,
                "frp": 4.5 + (i % 7) * 2.1,
                "daynight": "D",
                "type": 0,
                "notes": FIXTURE_NOTICE,
            }
        )
    return pd.DataFrame(rows)


def fixture_polygon_features() -> list[dict]:
    """Two FIRMS-shaped polygon features (simple squares) for unit tests."""
    def square(lon: float, lat: float, size: float = 0.2) -> dict:
        ring = [
            [lon, lat],
            [lon + size, lat],
            [lon + size, lat + size],
            [lon, lat + size],
            [lon, lat],
        ]
        return {
            "type": "Polygon",
            "coordinates": [ring],
        }

    return [
        {
            "type": "Feature",
            "properties": {
                "gfwid": "fixture-a",
                "name": "Fixture Concession A",
                "company": "Fixture Co A",
                "group_comp": "Fixture Group",
                "area_ha": 48000,
                "notes": FIXTURE_NOTICE,
            },
            "geometry": square(112.9, -2.1),
        },
        {
            "type": "Feature",
            "properties": {
                "gfwid": "fixture-b",
                "name": "Fixture Concession B",
                "company": "Fixture Co B",
                "group_comp": "Fixture Group",
                "area_ha": 12000,
                "notes": FIXTURE_NOTICE,
            },
            "geometry": square(113.3, -1.9, 0.1),
        },
    ]
