"""Unit tests: point-in-time feature building (future-data leakage must be impossible)."""

import pandas as pd

from haze_pipelines.build_features import build_features
from haze_pipelines.fixtures import fixture_hotspots, fixture_polygon_features
from haze_pipelines.ingest_firms import normalize_firms
from haze_pipelines.ingest_polygons import normalize_polygons
from haze_pipelines.quality import WEATHER_COLUMNS

POLYGONS = normalize_polygons(
    fixture_polygon_features(),
    source_dataset="FIXTURE",
    boundary_type="concession",
    license="test",
    vintage="2026",
    treatment="synthetic-fixture",
)[0]

WEATHER = pd.DataFrame(
    [
        {
            "station_id": "STN-1",
            "latitude": -2.0,
            "longitude": 113.0,
            "observation_time": pd.Timestamp("2026-01-01", tz="UTC"),
            "available_time": pd.Timestamp("2026-01-03", tz="UTC"),
            "temperature_max_c": 32.5,
            "precipitation_sum_mm": 5.0,
            "humidity_mean_pct": 75.0,
            "wind_max_ms": 10.0,
        },
        {
            "station_id": "STN-1",
            "latitude": -2.0,
            "longitude": 113.0,
            "observation_time": pd.Timestamp("2025-12-01", tz="UTC"),
            "available_time": pd.Timestamp("2025-12-03", tz="UTC"),
            "temperature_max_c": 31.0,
            "precipitation_sum_mm": 100.0,
            "humidity_mean_pct": 90.0,
            "wind_max_ms": 5.0,
        },
    ],
    columns=WEATHER_COLUMNS,
)


def _aerosol_row(
    grid_id: str,
    lat: float,
    lon: float,
    date: str,
    available: str,
    aod: float,
    pm25: float,
    pm10: float,
) -> dict:
    return {
        "grid_id": grid_id,
        "latitude": lat,
        "longitude": lon,
        "date": pd.Timestamp(date, tz="UTC"),
        "available_time": pd.Timestamp(available, tz="UTC"),
        "aerosol_optical_depth_mean": aod,
        "aerosol_optical_depth_max": aod * 2,
        "pm2_5_mean": pm25,
        "pm10_mean": pm10,
        "is_fixture": False,
        "source": "CAMS_via_OpenMeteo",
    }


AEROSOL = pd.DataFrame(
    [
        _aerosol_row("CAMS-NEAR", -2.0, 113.0, "2026-01-01", "2026-01-02", 0.4, 20.0, 30.0),
        _aerosol_row("CAMS-NEAR", -2.0, 113.0, "2026-01-02", "2026-01-03", 0.6, 40.0, 60.0),
        _aerosol_row("CAMS-FAR", 5.0, 120.0, "2026-01-02", "2026-01-03", 9.9, 999.0, 999.0),
        # Future observation must never leak into an earlier as_of.
        _aerosol_row("CAMS-NEAR", -2.0, 113.0, "2026-01-10", "2026-01-11", 5.0, 500.0, 500.0),
    ]
)


def test_features_count_only_data_available_at_as_of():
    raw = fixture_hotspots(n=8, start=pd.Timestamp("2026-01-01", tz="UTC").to_pydatetime())

    # Fast availability: observations count as soon as they are acquired.
    fast = normalize_firms(raw, source="FIXTURE", available_lag_hours=0.0, is_fixture=True)
    as_of = pd.Timestamp("2026-01-02", tz="UTC")
    feats_fast = build_features(POLYGONS, fast, WEATHER, as_of)

    # Slow availability: same observations, but not yet public at as_of.
    slow = normalize_firms(raw, source="FIXTURE", available_lag_hours=48.0, is_fixture=True)
    feats_slow = build_features(POLYGONS, slow, WEATHER, as_of)

    assert feats_fast["hotspot_count_7d"].sum() > feats_slow["hotspot_count_7d"].sum()
    assert feats_slow["hotspot_count_7d"].sum() >= 0


def test_weather_windows_use_only_recent_days():
    raw = normalize_firms(fixture_hotspots(n=4), source="FIXTURE", available_lag_hours=0.0, is_fixture=True)
    as_of = pd.Timestamp("2026-01-03", tz="UTC")
    feats = build_features(POLYGONS, raw, WEATHER, as_of)

    # Only the 2026-01-01 row falls in the 7-day window (2025-12-01 is stale).
    assert feats["temp_max_7d_c"].eq(32.5).all()
    assert feats["precip_sum_7d_mm"].eq(5.0).all()


def test_feature_schema_is_stable():
    raw = normalize_firms(fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True)
    feats = build_features(POLYGONS, raw, None, pd.Timestamp("2026-01-02", tz="UTC"))
    assert list(feats.columns) == [
        "polygon_id",
        "as_of",
        "hotspot_count_1d",
        "hotspot_count_7d",
        "hotspot_count_30d",
        "days_since_last_hotspot",
        "nearest_hotspot_km_7d",
        "temp_max_7d_c",
        "precip_sum_7d_mm",
        "humidity_mean_7d_pct",
        "wind_max_7d_ms",
        "weather_station_id",
        "weather_distance_km",
        "aerosol_optical_depth_mean_7d",
        "aerosol_optical_depth_max_7d",
        "pm2_5_mean_7d",
        "pm10_mean_7d",
        "haze_grid_id",
        "haze_distance_km",
    ]


def test_weather_comes_from_nearest_station_only():
    """Regression: weather used to pool ALL stations, so a Sumatra polygon got
    Kalimantan weather mixed in. Each polygon must use its nearest station."""
    two_stations = pd.DataFrame(
        [
            {
                "station_id": "STN-WEST",
                "latitude": -2.0,
                "longitude": 113.0,
                "observation_time": pd.Timestamp("2026-01-01", tz="UTC"),
                "available_time": pd.Timestamp("2026-01-01", tz="UTC"),
                "temperature_max_c": 30.0,
                "precipitation_sum_mm": 1.0,
                "humidity_mean_pct": 70.0,
                "wind_max_ms": 5.0,
            },
            {
                "station_id": "STN-EAST",
                "latitude": -2.0,
                "longitude": 118.0,
                "observation_time": pd.Timestamp("2026-01-01", tz="UTC"),
                "available_time": pd.Timestamp("2026-01-01", tz="UTC"),
                "temperature_max_c": 36.0,
                "precipitation_sum_mm": 20.0,
                "humidity_mean_pct": 50.0,
                "wind_max_ms": 15.0,
            },
        ],
        columns=WEATHER_COLUMNS,
    )
    east_polygon = pd.DataFrame(
        [
            {
                "polygon_id": "poly-east",
                "boundary_type": "concession",
                "source_dataset": "FIXTURE",
                "source_feature_id": "east",
                "company_attribution": None,
                "group_attribution": None,
                "attribution_confidence": "unverified",
                "area_ha": 10000.0,
                "area_source": "source_attribute",
                "vintage": "2026",
                "license": "test",
                "treatment": "synthetic-fixture",
                "centroid_lon": 118.0,
                "centroid_lat": -2.0,
                "geometry": "POLYGON ((117.9 -2.1, 118.1 -2.1, 118.1 -1.9, 117.9 -1.9, 117.9 -2.1))",
            }
        ]
    )
    polygons = pd.concat([POLYGONS, east_polygon], ignore_index=True)
    raw = normalize_firms(fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True)

    feats = build_features(polygons, raw, two_stations, pd.Timestamp("2026-01-02", tz="UTC"))
    by_id = feats.set_index("polygon_id")

    # Polygons A/B (near 113.0) use STN-WEST; the eastern polygon uses STN-EAST.
    assert by_id.loc["poly-east", "weather_station_id"] == "STN-EAST"
    assert by_id.loc["poly-east", "temp_max_7d_c"] == 36.0
    assert by_id.loc["poly-east", "precip_sum_7d_mm"] == 20.0
    west_rows = by_id.drop(index="poly-east")
    assert (west_rows["weather_station_id"] == "STN-WEST").all()
    assert (west_rows["temp_max_7d_c"] == 30.0).all()
    # Pooled weather (the old bug) would have produced 33.0 everywhere.
    assert not (by_id["temp_max_7d_c"] == 33.0).any()
    # Distances are recorded for auditability.
    assert by_id["weather_distance_km"].notna().all()


def test_haze_comes_from_nearest_grid_point_and_respects_availability():
    """CAMS rows are filtered on available_time and joined to the nearest point."""
    raw = normalize_firms(
        fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True
    )
    # as_of 2026-01-03: only the two Jan-1/Jan-2 rows are available (Jan-10 is not).
    feats = build_features(
        POLYGONS, raw, WEATHER, pd.Timestamp("2026-01-03", tz="UTC"), aerosol=AEROSOL
    )
    first = feats.iloc[0]

    assert first["haze_grid_id"] == "CAMS-NEAR"
    assert first["haze_distance_km"] < 10.0
    assert first["aerosol_optical_depth_mean_7d"] == 0.5  # mean(0.4, 0.6)
    assert first["aerosol_optical_depth_max_7d"] == 1.2  # max(0.8, 1.2)
    assert first["pm2_5_mean_7d"] == 30.0
    assert first["pm10_mean_7d"] == 45.0


def test_haze_is_empty_when_no_observation_is_available_yet():
    raw = normalize_firms(
        fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True
    )
    feats = build_features(
        POLYGONS, raw, WEATHER, pd.Timestamp("2026-01-01", tz="UTC"), aerosol=AEROSOL
    )
    first = feats.iloc[0]

    # Nothing was public yet, so no grid point or value is borrowed.
    assert first["haze_grid_id"] is None
    assert pd.isna(first["aerosol_optical_depth_mean_7d"])
    assert pd.isna(first["pm2_5_mean_7d"])
