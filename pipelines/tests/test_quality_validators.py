"""Tests for the feature and forecast validators (routing regression)."""

import pandas as pd

from haze_pipelines.quality import (
    AEROSOL_COLUMNS,
    FEATURE_COLUMNS,
    FORECAST_COLUMNS,
    validate_aerosol,
    validate_exposure,
    validate_features,
    validate_forecast,
)


def _features_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "polygon_id": "poly_a",
                "as_of": pd.Timestamp("2026-02-01", tz="UTC"),
                "hotspot_count_1d": 1,
                "hotspot_count_7d": 3,
                "hotspot_count_30d": 8,
                "days_since_last_hotspot": 2.0,
                "nearest_hotspot_km_7d": 5.0,
                "temp_max_7d_c": 32.0,
                "precip_sum_7d_mm": 10.0,
                "humidity_mean_7d_pct": 70.0,
                "wind_max_7d_ms": 8.0,
                "weather_station_id": "STN-1",
                "weather_distance_km": 12.0,
            },
            {
                "polygon_id": "poly_b",
                "as_of": pd.Timestamp("2026-02-01", tz="UTC"),
                "hotspot_count_1d": 0,
                "hotspot_count_7d": 0,
                "hotspot_count_30d": 0,
                "days_since_last_hotspot": float("nan"),
                "nearest_hotspot_km_7d": float("nan"),
                "temp_max_7d_c": 30.0,
                "precip_sum_7d_mm": 5.0,
                "humidity_mean_7d_pct": 65.0,
                "wind_max_7d_ms": 6.0,
                "weather_station_id": "STN-2",
                "weather_distance_km": 40.0,
            },
        ],
        columns=FEATURE_COLUMNS,
    )


def _forecast_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "polygon_id": "poly_a",
                "as_of": pd.Timestamp("2026-02-01", tz="UTC"),
                "horizon_hours": 24,
                "hazard_score": 0.62,
                "model_name": "persistence_recency_baseline",
                "model_version": "0.1.0",
                "data_type": "baseline",
                "disclaimer": "Baseline hazard score - not a calibrated probability.",
            }
        ],
        columns=FORECAST_COLUMNS,
    )


def test_feature_validator_passes_on_good_data():
    report = validate_features(_features_df())
    assert report.passed, [c.name for c in report.errors]


def test_feature_validator_flags_window_monotonicity_violation():
    df = _features_df()
    df.loc[0, ["hotspot_count_1d", "hotspot_count_7d", "hotspot_count_30d"]] = [9, 3, 1]
    report = validate_features(df)
    assert not report.passed
    assert any(c.name == "window_monotonic" and not c.passed for c in report.checks)


def test_forecast_validator_passes_on_good_data():
    report = validate_forecast(_forecast_df())
    assert report.passed, [c.name for c in report.errors]


def test_forecast_validator_flags_out_of_range_score():
    df = _forecast_df()
    df.loc[0, "hazard_score"] = 1.5
    report = validate_forecast(df)
    assert not report.passed
    assert any(c.name == "hazard_score_in_range" and not c.passed for c in report.checks)


def test_forecast_validator_requires_baseline_labeling():
    df = _forecast_df()
    df.loc[0, "disclaimer"] = None
    report = validate_forecast(df)
    assert any(c.name == "labeled_baseline" and not c.passed for c in report.checks)


def test_exposure_validator_rejects_null_counts():
    df = pd.DataFrame(
        {
            "polygon_id": ["poly_a", "poly_b"],
            "hotspot_count_in_polygon_30d": [0.0, float("nan")],
            "hotspot_count_near_30d": [1.0, 2.0],
        }
    )
    report = validate_exposure(df)
    assert not report.passed
    assert any(c.name == "counts_non_negative" and not c.passed for c in report.checks)


def _aerosol_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "available_time": pd.Timestamp("2026-01-04", tz="UTC"),
                "grid_id": "CAMS-113.90_-2.20",
                "latitude": -2.2,
                "longitude": 113.9,
                "aerosol_optical_depth_mean": 0.4,
                "aerosol_optical_depth_max": 0.8,
                "pm2_5_mean": 20.0,
                "pm10_mean": 30.0,
                "is_fixture": False,
                "source": "CAMS_via_OpenMeteo",
            }
        ],
        columns=AEROSOL_COLUMNS,
    )


def test_aerosol_validator_passes_on_good_data():
    report = validate_aerosol(_aerosol_df())
    assert report.passed, [c.name for c in report.errors]


def test_aerosol_validator_flags_negative_values():
    df = _aerosol_df()
    df.loc[0, "pm2_5_mean"] = -1.0
    report = validate_aerosol(df)
    assert not report.passed
    assert any(c.name == "aerosol_non_negative" and not c.passed for c in report.checks)
