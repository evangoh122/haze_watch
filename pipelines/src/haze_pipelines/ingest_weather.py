"""Weather ingestion from Open-Meteo's historical API (ERA5 reanalysis).

Public, key-free source (https://open-meteo.com/). Daily aggregates are used to
keep datasets portable. Daily values are treated as available 48 hours after the
observation day (conservative reanalysis latency) for point-in-time correctness.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

from .config import Settings, settings
from .geo import INDONESIA_BBOX
from .io import write_parquet

DAILY_VARS = [
    "temperature_2m_max",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
]

CANONICAL_COLUMNS = [
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


def _coord_label(value: float, positive: str, negative: str) -> str:
    return f"{abs(value):.0f}{positive if value >= 0 else negative}"


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
        f"era5-{station['station_id']}-"
        f"{float(station['latitude']):.4f}-{float(station['longitude']):.4f}-"
        f"{_day_key(start_date)}-{_day_key(end_date)}.parquet"
    )


def grid_stations(
    bbox: tuple[float, float, float, float] = INDONESIA_BBOX,
    grid: int = 6,
) -> list[dict]:
    """Build a regular ERA5 point grid as station rows.

    ERA5 is a reanalysis grid, not a station network. A regular grid gives every
    concession an auditable nearest point instead of stretching four distant
    stations across the archipelago (the old demo used one station for 207 km to
    824 km away). ``grid`` is the number of points per axis, inclusive.
    """
    if grid < 2:
        raise ValueError("grid must be >= 2")
    min_lon, min_lat, max_lon, max_lat = bbox
    lons = [min_lon + i * (max_lon - min_lon) / (grid - 1) for i in range(grid)]
    lats = [min_lat + i * (max_lat - min_lat) / (grid - 1) for i in range(grid)]
    stations: list[dict] = []
    for lat in lats:
        for lon in lons:
            station_id = (
                f"ERA5-{_coord_label(lon, 'E', 'W')}-{_coord_label(lat, 'N', 'S')}"
            )
            stations.append(
                {
                    "station_id": station_id,
                    "label": f"ERA5 grid point {lat:.2f},{lon:.2f}",
                    "latitude": lat,
                    "longitude": lon,
                }
            )
    return stations


def fetch_station_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    *,
    base_url: str | None = None,
    client: httpx.Client | None = None,
    max_retries: int = 5,
    retry_wait_seconds: float = 60.0,
) -> dict:
    """Fetch daily reanalysis values for one point. Returns the raw JSON payload.

    Long archive requests are metered by Open-Meteo's minutely quota. A 429 is a
    wait-and-retry signal, not a permanent failure; the caller also paces between
    stations.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "timezone": "UTC",
    }
    own_client = client is None
    client = client or httpx.Client(timeout=120.0)
    try:
        for attempt in range(max_retries + 1):
            response = client.get(
                base_url or settings.open_meteo_archive_url, params=params, timeout=120.0
            )
            if getattr(response, "status_code", 200) == 429 and attempt < max_retries:
                time.sleep(retry_wait_seconds)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("unreachable: weather retry loop exhausted")
    finally:
        if own_client:
            client.close()


def normalize_station_payload(
    payload: dict,
    station_id: str,
    *,
    availability_lag_hours: float | None = None,
) -> pd.DataFrame:
    """Normalize one station payload to the canonical weather schema."""
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    if not times:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    lag = (
        availability_lag_hours
        if availability_lag_hours is not None
        else settings.weather_availability_lag_hours
    )
    obs_time = pd.to_datetime(times, utc=True)

    df = pd.DataFrame(
        {
            "station_id": station_id,
            "latitude": float(payload["latitude"]),
            "longitude": float(payload["longitude"]),
            "observation_time": obs_time,
            "available_time": obs_time + pd.to_timedelta(lag, unit="h"),
            "temperature_max_c": daily.get("temperature_2m_max", [float("nan")] * len(times)),
            "precipitation_sum_mm": daily.get("precipitation_sum", [float("nan")] * len(times)),
            "humidity_mean_pct": daily.get("relative_humidity_2m_mean", [float("nan")] * len(times)),
            "wind_max_ms": daily.get("wind_speed_10m_max", [float("nan")] * len(times)),
        }
    )
    return df[CANONICAL_COLUMNS]


def ingest_stations(
    stations: list[dict],
    start_date: str,
    end_date: str,
    out_path: Path,
    *,
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
    pause_seconds: float = 0.0,
    max_retries: int = 5,
    checkpoint_dir: Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Fetch and normalize daily weather for a list of stations.

    Each station dict: ``{"station_id", "label", "latitude", "longitude"}``.
    With ``checkpoint_dir``, each completed station is written independently and
    skipped on a rerun, so a quota failure costs one station rather than the run.
    """
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for index, station in enumerate(stations):
        checkpoint_path = (
            _checkpoint_path(checkpoint_dir, station, start_date, end_date)
            if checkpoint_dir is not None
            else None
        )
        if checkpoint_path is not None and checkpoint_path.exists():
            frames.append(pd.read_parquet(checkpoint_path))
            continue

        payload = fetch_station_daily(
            station["latitude"],
            station["longitude"],
            start_date,
            end_date,
            base_url=settings_obj.open_meteo_archive_url,
            client=client,
            max_retries=max_retries,
        )
        frame = normalize_station_payload(
            payload,
            station["station_id"],
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
    ) if frames else pd.DataFrame(columns=CANONICAL_COLUMNS)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(
        df,
        out_path,
        extra_metadata={"dataset": "weather_observations", "source": "Open-Meteo/ERA5 (real)"},
    )
    from .provenance import register_dataset

    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="weather_observations::open_meteo",
        name="Daily weather observations (Open-Meteo / ERA5 reanalysis)",
        source=settings_obj.open_meteo_archive_url,
        license="Open-Meteo / Copernicus ERA5 terms (attribution required)",
        treatment="real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["observation_time"].min()) if len(df) else None,
        observation_end=str(df["observation_time"].max()) if len(df) else None,
        notes="Daily aggregates assumed available 48h after observation day (point-in-time safety).",
    )
    return df, out_path
