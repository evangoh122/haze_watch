"""Weather ingestion from NASA POWER (MERRA-2) as an ERA5 fallback.

Open-Meteo's free ERA5 archive is excellent but metered by request volume; a
full 1940+ sweep can exhaust the hourly quota before the panel is written.
NASA POWER serves daily MERRA-2 reanalysis with a point API, no key and much
looser limits, so it is the fallback for the historical weather panel.

MERRA-2 is a reanalysis, not a forecast. It is **not** ERA5; provenance records
the source explicitly. Missing values are returned as ``-999.0`` and are mapped
to NaN, never treated as observations.

Usage:
    haze-pipelines ingest-power --stations data/raw/weather/era5_coverage_5.csv \
        --start 1981-01-01 --end 2026-10-17 --out data/processed/weather.parquet
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

from .config import Settings, settings
from .ingest_weather import CANONICAL_COLUMNS
from .io import write_parquet

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_VARS = ("T2M_MAX", "PRECTOTCORR", "RH2M", "WS10M_MAX")
MISSING = -999.0

POWER_NOTE = (
    "NASA POWER / MERRA-2 daily reanalysis (fallback when the free Open-Meteo "
    "ERA5 archive quota is exhausted). MERRA-2 is not ERA5; missing -999 values "
    "are mapped to NaN."
)


def _day_key(value: str) -> str:
    return value.replace("-", "")


def _checkpoint_path(
    checkpoint_dir: Path,
    station: dict,
    start_date: str,
    end_date: str,
) -> Path:
    """A checkpoint is only valid for one source, point and requested window."""
    return checkpoint_dir / (
        f"power-{station['station_id']}-"
        f"{float(station['latitude']):.4f}-{float(station['longitude']):.4f}-"
        f"{_day_key(start_date)}-{_day_key(end_date)}.parquet"
    )


def fetch_power_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 120.0,
    max_retries: int = 5,
    retry_wait_seconds: float = 30.0,
) -> dict:
    """Fetch daily MERRA-2 values for one point. Returns the raw JSON payload."""
    params = {
        "parameters": ",".join(POWER_VARS),
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": _day_key(start_date),
        "end": _day_key(end_date),
        "format": "JSON",
    }
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        for attempt in range(max_retries + 1):
            response = client.get(API_URL, params=params, timeout=timeout)
            if getattr(response, "status_code", 200) == 429 and attempt < max_retries:
                time.sleep(retry_wait_seconds)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        else:  # pragma: no cover - defensive; loop always breaks or raises
            raise RuntimeError("unreachable: NASA POWER retry loop exhausted")
    finally:
        if own_client:
            client.close()
    if not isinstance(payload, dict):
        raise TypeError(f"unexpected NASA POWER payload: {type(payload).__name__}")
    return payload


def normalize_power_payload(
    payload: dict,
    station_id: str,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    availability_lag_hours: float | None = None,
) -> pd.DataFrame:
    """Normalize a NASA POWER daily payload to the canonical weather schema."""
    parameters = (payload.get("properties") or {}).get("parameter") or {}
    if not parameters:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    coordinates = (payload.get("geometry") or {}).get("coordinates") or [0.0, 0.0]
    lat = float(latitude if latitude is not None else coordinates[1])
    lon = float(longitude if longitude is not None else coordinates[0])

    days = sorted(
        {
            day
            for values in parameters.values()
            if isinstance(values, dict)
            for day in values
        }
    )
    lag = (
        availability_lag_hours
        if availability_lag_hours is not None
        else settings.weather_availability_lag_hours
    )
    rows: list[dict] = []
    for day in days:
        values = {
            name: parameters.get(name, {}).get(day)
            for name in POWER_VARS
        }
        if all(value in (None, MISSING) for value in values.values()):
            continue  # NASA POWER tail rows can be entirely missing
        obs = pd.Timestamp(day, tz="UTC")
        rows.append(
            {
                "station_id": station_id,
                "latitude": lat,
                "longitude": lon,
                "observation_time": obs,
                "available_time": obs + pd.to_timedelta(lag, unit="h"),
                "temperature_max_c": _clean(values["T2M_MAX"]),
                "precipitation_sum_mm": _clean(values["PRECTOTCORR"]),
                "humidity_mean_pct": _clean(values["RH2M"]),
                "wind_max_ms": _clean(values["WS10M_MAX"]),
            }
        )
    return pd.DataFrame(rows, columns=CANONICAL_COLUMNS)


def _clean(value: float | None) -> float:
    if value is None or value == MISSING:
        return float("nan")
    return float(value)


def ingest_stations(
    stations: list[dict],
    start_date: str,
    end_date: str,
    out_path: Path,
    *,
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
    pause_seconds: float = 1.0,
    max_retries: int = 5,
    checkpoint_dir: Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Fetch and normalize daily MERRA-2 weather for a list of points."""
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for index, station in enumerate(stations):
        checkpoint_path = (
            _checkpoint_path(checkpoint_dir, station, start_date, end_date)
            if checkpoint_dir is not None
            else None
        )
        if checkpoint_path is not None and checkpoint_path.exists():
            frames.append(pd.read_parquet(checkpoint_path))
            continue

        payload = fetch_power_daily(
            station["latitude"],
            station["longitude"],
            start_date,
            end_date,
            client=client,
            max_retries=max_retries,
        )
        frame = normalize_power_payload(
            payload,
            station["station_id"],
            latitude=station["latitude"],
            longitude=station["longitude"],
            availability_lag_hours=settings_obj.weather_availability_lag_hours,
        )
        if checkpoint_path is not None:
            write_parquet(
                frame,
                checkpoint_path,
                extra_metadata={"dataset": "weather_observations_partial"},
            )
        frames.append(frame)
        if index < len(stations) - 1 and pause_seconds > 0:
            time.sleep(pause_seconds)

    df = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["station_id", "observation_time"])
        .reset_index(drop=True)
        if frames
        else pd.DataFrame(columns=CANONICAL_COLUMNS)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(
        df,
        out_path,
        extra_metadata={"dataset": "weather_observations", "source": "NASA POWER / MERRA-2"},
    )
    from .provenance import register_dataset

    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="weather_observations::nasa_power",
        name="Daily weather observations (NASA POWER / MERRA-2 reanalysis)",
        source=f"{API_URL} (stations={len(stations)}, {start_date}..{end_date})",
        license="NASA POWER open data (attribution required)",
        treatment="real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["observation_time"].min()) if len(df) else None,
        observation_end=str(df["observation_time"].max()) if len(df) else None,
        notes=POWER_NOTE,
    )
    return df, out_path
