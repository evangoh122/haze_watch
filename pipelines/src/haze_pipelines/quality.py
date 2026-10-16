"""Data-quality checks.

Checks follow project_profile.md section 11 (data tests): coordinate ranges,
polygon geometry validity, duplicate hotspots, temporal alignment, availability
timestamps and missingness. Every check reports a machine-readable result so the
quality report can be asserted in CI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import shapely.wkt

HOTSPOT_COLUMNS = [
    "hotspot_id",
    "source",
    "satellite",
    "latitude",
    "longitude",
    "observation_time",
    "available_time",
    "brightness_k",
    "frp_mw",
    "confidence_pct",
    "daynight",
    "is_fixture",
]

WEATHER_COLUMNS = [
    "station_id",
    "latitude",
    "longitude",
    "observation_time",
    "available_time",
    "temperature_max_c",
    "precipitation_sum_mm",
    "humidity_mean_pct",
    "wind_max_ms",
]

FEATURE_COLUMNS = [
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
]

FORECAST_COLUMNS = [
    "polygon_id",
    "as_of",
    "horizon_hours",
    "hazard_score",
    "model_name",
    "model_version",
    "data_type",
    "disclaimer",
]


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str  # "error" | "warning"
    message: str
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "count": self.count,
        }


@dataclass
class QualityReport:
    dataset: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "error")

    @property
    def errors(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    def add(self, name: str, passed: bool, message: str, *, severity: str = "error", count: int = 0) -> None:
        self.checks.append(CheckResult(name, passed, severity, message, count))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
        }


def validate_hotspots(df: pd.DataFrame, *, dataset: str = "fire_hotspots") -> QualityReport:
    """Validate a normalized hotspot table."""
    report = QualityReport(dataset)

    missing = [c for c in HOTSPOT_COLUMNS if c not in df.columns]
    report.add(
        "schema_complete",
        not missing,
        "all required columns present" if not missing else f"missing columns: {missing}",
        count=len(missing),
    )
    if missing:
        return report

    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    bad_coords = df[(df["latitude"].abs() > 90) | (df["longitude"].abs() > 180)]
    report.add(
        "coordinate_ranges",
        len(bad_coords) == 0,
        "lat/lon within valid ranges" if len(bad_coords) == 0 else "out-of-range coordinates",
        count=len(bad_coords),
    )

    null_critical = df[["latitude", "longitude", "observation_time", "available_time"]].isna().any(axis=1)
    report.add(
        "no_null_critical_fields",
        int(null_critical.sum()) == 0,
        "coordinates and timestamps populated",
        count=int(null_critical.sum()),
    )

    dup_key = ["source", "latitude", "longitude", "observation_time"]
    duplicates = df.duplicated(subset=dup_key, keep=False)
    report.add(
        "no_duplicate_hotspots",
        int(duplicates.sum()) == 0,
        "no duplicate (source, location, observation_time) rows",
        count=int(duplicates.sum()),
    )

    obs = pd.to_datetime(df["observation_time"], utc=True, errors="coerce")
    avail = pd.to_datetime(df["available_time"], utc=True, errors="coerce")
    unparseable = int(obs.isna().sum() + avail.isna().sum())
    report.add(
        "timestamps_parseable",
        unparseable == 0,
        "observation and availability timestamps parse as UTC",
        count=unparseable,
    )

    future_availability = int((avail < obs).sum())
    report.add(
        "availability_not_before_observation",
        future_availability == 0,
        "available_time is never earlier than observation_time",
        count=future_availability,
    )

    conf = df["confidence_pct"]
    bad_conf = int(((conf < 0) | (conf > 100)).sum())
    report.add(
        "confidence_in_range",
        bad_conf == 0,
        "confidence within 0-100",
        count=bad_conf,
    )

    missingness = df[HOTSPOT_COLUMNS].isna().mean().mean()
    report.add(
        "missingness_below_threshold",
        missingness < 0.05,
        f"mean missingness {missingness:.3f} (<0.05)",
        severity="warning",
        count=0,
    )
    return report


def validate_polygons(df: pd.DataFrame, *, dataset: str = "polygons") -> QualityReport:
    """Validate a polygon table with a WKT ``geometry`` column."""
    report = QualityReport(dataset)
    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    if "geometry" not in df.columns:
        report.add("geometry_column", False, "missing 'geometry' WKT column")
        return report

    invalid = 0
    empty = 0
    for wkt in df["geometry"]:
        try:
            geom = shapely.wkt.loads(wkt)
        except Exception:  # noqa: BLE001 - unparseable WKT counts as invalid geometry
            invalid += 1
            continue
        if geom.is_empty:
            empty += 1
        elif not geom.is_valid:
            invalid += 1
    report.add(
        "geometry_valid",
        invalid == 0,
        "all geometries parse and are valid" if invalid == 0 else f"{invalid} invalid geometries",
        count=invalid,
    )
    report.add(
        "geometry_non_empty",
        empty == 0,
        "no empty geometries",
        count=empty,
    )

    if "polygon_id" in df.columns:
        dupes = int(df.duplicated(subset=["polygon_id"]).sum())
        report.add("unique_polygon_ids", dupes == 0, "polygon_id is unique", count=dupes)

    if "vintage" in df.columns:
        missing_vintage = int(df["vintage"].isna().sum())
        report.add(
            "vintage_recorded",
            missing_vintage == 0,
            "boundary vintage recorded for attribution uncertainty",
            count=missing_vintage,
        )
    return report


def validate_weather(df: pd.DataFrame, *, dataset: str = "weather") -> QualityReport:
    """Validate a normalized weather observation table."""
    report = QualityReport(dataset)
    missing = [c for c in WEATHER_COLUMNS if c not in df.columns]
    report.add(
        "schema_complete",
        not missing,
        "all required columns present" if not missing else f"missing columns: {missing}",
        count=len(missing),
    )
    if missing:
        return report

    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    dupes = int(df.duplicated(subset=["station_id", "observation_time"]).sum())
    report.add("no_duplicate_station_days", dupes == 0, "unique (station, day)", count=dupes)

    obs = pd.to_datetime(df["observation_time"], utc=True, errors="coerce")
    avail = pd.to_datetime(df["available_time"], utc=True, errors="coerce")
    report.add(
        "availability_after_observation",
        int((avail < obs).sum()) == 0,
        "available_time >= observation_time",
        count=int((avail < obs).sum()),
    )

    precip_negative = int((df["precipitation_sum_mm"] < 0).sum())
    report.add("precipitation_non_negative", precip_negative == 0, "precipitation >= 0", count=precip_negative)

    return report


def validate_features(df: pd.DataFrame, *, dataset: str = "environmental_features") -> QualityReport:
    """Validate a point-in-time feature table."""
    report = QualityReport(dataset)
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    report.add(
        "schema_complete",
        not missing,
        "all required columns present" if not missing else f"missing columns: {missing}",
        count=len(missing),
    )
    if missing:
        return report

    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    dupes = int(df.duplicated(subset=["polygon_id", "as_of"]).sum())
    report.add("unique_polygon_asof", dupes == 0, "unique (polygon_id, as_of)", count=dupes)

    # Hotspot counts must be non-negative integers.
    counts = df[["hotspot_count_1d", "hotspot_count_7d", "hotspot_count_30d"]]
    negative_counts = int((counts < 0).sum().sum())
    report.add("counts_non_negative", negative_counts == 0, "hotspot counts >= 0", count=negative_counts)

    # Point-in-time monotonicity: 1d <= 7d <= 30d windows.
    monotonic = (df["hotspot_count_1d"] <= df["hotspot_count_7d"]) & (
        df["hotspot_count_7d"] <= df["hotspot_count_30d"]
    )
    violations = int((~monotonic).sum())
    report.add(
        "window_monotonic",
        violations == 0,
        "1d <= 7d <= 30d window counts",
        count=violations,
    )
    return report


def validate_exposure(df: pd.DataFrame, *, dataset: str = "exposure") -> QualityReport:
    """Validate a per-polygon exposure table."""
    report = QualityReport(dataset)
    required = ["polygon_id", "hotspot_count_in_polygon_30d", "hotspot_count_near_30d"]
    missing = [c for c in required if c not in df.columns]
    report.add(
        "schema_complete",
        not missing,
        "all required columns present" if not missing else f"missing columns: {missing}",
        count=len(missing),
    )
    if missing:
        return report

    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    negative = int((df[["hotspot_count_in_polygon_30d", "hotspot_count_near_30d"]] < 0).sum().sum())
    report.add("counts_non_negative", negative == 0, "detection counts >= 0", count=negative)

    # Near-buffer counts must include in-polygon detections.
    inconsistent = int((df["hotspot_count_near_30d"] < df["hotspot_count_in_polygon_30d"]).sum())
    report.add(
        "near_superset_of_polygon",
        inconsistent == 0,
        "near counts >= in-polygon counts",
        count=inconsistent,
    )
    return report


def validate_forecast(df: pd.DataFrame, *, dataset: str = "fire_forecast_baseline") -> QualityReport:
    """Validate a baseline forecast table."""
    report = QualityReport(dataset)
    missing = [c for c in FORECAST_COLUMNS if c not in df.columns]
    report.add(
        "schema_complete",
        not missing,
        "all required columns present" if not missing else f"missing columns: {missing}",
        count=len(missing),
    )
    if missing:
        return report

    report.add("non_empty", len(df) > 0, f"{len(df)} rows", count=len(df))

    out_of_range = int(((df["hazard_score"] < 0) | (df["hazard_score"] > 1)).sum())
    report.add(
        "hazard_score_in_range",
        out_of_range == 0,
        "hazard_score within [0, 1]",
        count=out_of_range,
    )

    bad_horizon = int((~df["horizon_hours"].isin([24, 48, 72])).sum())
    report.add(
        "horizon_supported",
        bad_horizon == 0,
        "horizon_hours in {24, 48, 72}",
        count=bad_horizon,
    )

    # Must always carry the baseline disclaimer and model identity.
    unlabeled = int(df["disclaimer"].isna().sum() + df["model_name"].isna().sum())
    report.add(
        "labeled_baseline",
        unlabeled == 0,
        "disclaimer and model_name populated",
        count=unlabeled,
    )
    return report
