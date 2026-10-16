"""NASA FIRMS active-fire hotspot ingestion.

Accepts FIRMS CSV exports (MODIS or VIIRS column layouts) from ``data/raw/firms/``
or fetches an area extract from the FIRMS API when ``FIRMS_API_KEY`` is configured.

Real observations only: any fixture data must be generated via
``haze_pipelines.fixtures`` and is labeled ``is_fixture=True``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pandas as pd

from .config import Settings, settings
from .geo import INDONESIA_BBOX, in_bbox

# Column layouts of FIRMS CSV exports (MODIS C6.1 and VIIRS 375m).
# Real FIRMS exports use acq_date / acq_time (acq_time is an HHMM integer such as
# 430 or 1830); some derived exports use acquired_date / acquired_time ("HH:MM").
_DATE_COLUMNS = ("acq_date", "acquired_date")
_TIME_COLUMNS = ("acq_time", "acquired_time")
_BRIGHTNESS_COLUMNS = ("brightness", "bright_ti4", "bright_ti5", "brightness_1")
_CONFIDENCE_LABELS = {"low": 30.0, "nominal": 60.0, "high": 90.0}

CANONICAL_COLUMNS = [
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


def _hotspot_id(source: str, lat: float, lon: float, obs_time_iso: str) -> str:
    raw = f"{source}|{lat:.5f}|{lon:.5f}|{obs_time_iso}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _confidence_to_pct(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    if isinstance(value, str):
        label = value.strip().lower()
        if label in _CONFIDENCE_LABELS:
            return _CONFIDENCE_LABELS[label]
        try:
            return float(label)
        except ValueError:
            return float("nan")
    return float(value)


def _normalize_time_value(value: object) -> str:
    """Normalize an acquisition time to ``HH:MM``.

    Real FIRMS exports store ``acq_time`` as an HHMM integer (430 -> 04:30,
    1830 -> 18:30); derived exports may already use ``HH:MM`` strings.
    """
    text = str(value).strip()
    text = text.removesuffix(".0")
    if text.isdigit():
        padded = text.zfill(4)
        hours, minutes = int(padded[:2]), int(padded[2:])
        if hours > 23 or minutes > 59:
            return "invalid"
        return f"{padded[:2]}:{padded[2:]}"
    return text


def normalize_firms(
    raw: pd.DataFrame,
    *,
    source: str,
    available_lag_hours: float,
    is_fixture: bool = False,
) -> pd.DataFrame:
    """Normalize a raw FIRMS export to the canonical hotspot schema.

    Accepts both real FIRMS exports (``acq_date``/``acq_time`` HHMM) and derived
    exports (``acquired_date``/``acquired_time`` HH:MM).

    - ``observation_time``: acquisition timestamp, UTC.
    - ``available_time``: observation_time + availability lag (point-in-time safety).
    """
    df = raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    date_col = next((c for c in _DATE_COLUMNS if c in df.columns), None)
    time_col = next((c for c in _TIME_COLUMNS if c in df.columns), None)
    missing = {"latitude", "longitude"} - set(df.columns)
    if date_col is None or time_col is None:
        missing |= {"acq_date", "acq_time"}
    if missing:
        raise ValueError(
            f"FIRMS export missing required columns: {sorted(missing)} "
            "(expected real FIRMS schema acq_date/acq_time or derived acquired_date/acquired_time)"
        )

    obs_time = pd.to_datetime(
        df[date_col].astype(str).str.strip()
        + " "
        + df[time_col].map(_normalize_time_value),
        format="mixed",
        utc=True,
        errors="coerce",
    )
    if obs_time.isna().any():
        raise ValueError(f"{int(obs_time.isna().sum())} rows have unparseable acquisition timestamps")

    brightness_col = next((c for c in _BRIGHTNESS_COLUMNS if c in df.columns), None)

    out = pd.DataFrame(
        {
            "source": source,
            "satellite": df.get("satellite", pd.Series(["unknown"] * len(df))).astype(str).str.strip(),
            "latitude": df["latitude"].astype(float),
            "longitude": df["longitude"].astype(float),
            "observation_time": obs_time,
            "available_time": obs_time + pd.to_timedelta(available_lag_hours, unit="h"),
            "brightness_k": df[brightness_col].astype(float) if brightness_col else float("nan"),
            "frp_mw": df["frp"].astype(float) if "frp" in df.columns else float("nan"),
            "confidence_pct": df["confidence"].map(_confidence_to_pct) if "confidence" in df.columns else float("nan"),
            "daynight": df.get("daynight", pd.Series(["unknown"] * len(df))).astype(str).str.strip(),
            "is_fixture": bool(is_fixture),
        }
    )

    out.insert(
        0,
        "hotspot_id",
        [
            _hotspot_id(source, lat, lon, ts.isoformat())
            for lat, lon, ts in zip(out["latitude"], out["longitude"], out["observation_time"])
        ],
    )
    # Exact duplicates (same source, location and acquisition time) collapse to one row.
    return out.drop_duplicates(subset=["hotspot_id"])[CANONICAL_COLUMNS].reset_index(drop=True)


def read_firms_csvs(
    input_dir: Path,
    *,
    source: str = "NASA_FIRMS",
    available_lag_hours: float | None = None,
    is_fixture: bool = False,
) -> pd.DataFrame:
    """Read and normalize every FIRMS CSV in a directory, deduplicating rows."""
    lag = available_lag_hours if available_lag_hours is not None else settings.firms_availability_lag_hours
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no FIRMS CSV files found in {input_dir}")

    frames = [normalize_firms(pd.read_csv(f), source=source, available_lag_hours=lag, is_fixture=is_fixture) for f in files]
    merged = pd.concat(frames, ignore_index=True)
    return merged.drop_duplicates(subset=["hotspot_id"]).reset_index(drop=True)


def fetch_firms_area(
    area: str,
    days: int,
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    sensor: str = "MODIS_NRT",
) -> pd.DataFrame:
    """Fetch an area extract from the FIRMS CSV API (requires FIRMS_API_KEY).

    ``area`` is ``west,south,east,north`` (a WGS84 bounding box) and ``days`` the
    trailing window (1-10). See https://firms.modaps.eosdis.nasa.gov/api/area/.
    """
    key = api_key if api_key is not None else settings.firms_api_key
    if not key:
        raise RuntimeError(
            "FIRMS API key not configured. Set FIRMS_API_KEY (alias "
            "HAZE_FIRMS_API_KEY) for automatic pulls, or place CSV exports in "
            "data/raw/firms/ and ingest without --from-api."
        )
    if days < 1 or days > 10:
        raise ValueError("FIRMS area API supports 1-10 days per request")

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{sensor}/{area}/{days}"
    own_client = client is None
    client = client or httpx.Client(timeout=60.0)
    try:
        response = client.get(url)
        response.raise_for_status()
    finally:
        if own_client:
            client.close()

    from io import StringIO

    return normalize_firms(
        pd.read_csv(StringIO(response.text)),
        source=f"NASA_FIRMS_{sensor}",
        available_lag_hours=settings.firms_availability_lag_hours,
    )


def indonesia_bbox_check(df: pd.DataFrame) -> pd.Series:
    """Boolean mask: rows whose coordinates fall inside the Indonesia bbox."""
    return df.apply(lambda r: in_bbox(r["longitude"], r["latitude"], INDONESIA_BBOX), axis=1)


def default_area(bbox: tuple[float, float, float, float] = INDONESIA_BBOX) -> str:
    """FIRMS ``area`` string (``west,south,east,north``) for a bounding box."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


def ingest_from_api(
    out_path: Path,
    *,
    area: str | None = None,
    days: int = 3,
    sensor: str = "MODIS_NRT",
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Automatic pull: fetch recent FIRMS detections and persist them.

    Requires a free FIRMS MAP_KEY (``FIRMS_API_KEY`` / ``HAZE_FIRMS_API_KEY``).
    Defaults to the Indonesia bounding box and the trailing ``days`` window.
    Registered with treatment ``real`` - never ``synthetic-fixture``.
    """
    resolved_area = area or default_area()
    df = fetch_firms_area(
        resolved_area,
        days,
        api_key=settings_obj.firms_api_key,
        client=client,
        sensor=sensor,
    )

    from .io import write_parquet
    from .provenance import register_dataset

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(
        df,
        out_path,
        extra_metadata={"dataset": "fire_hotspots", "source": f"NASA_FIRMS API ({sensor})"},
    )
    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="fire_hotspots::nasa_firms",
        name="Active fire hotspots (NASA FIRMS)",
        source=f"NASA FIRMS area API (sensor={sensor}, area={resolved_area}, days={days})",
        license="NASA FIRMS terms (attribution required)",
        treatment="real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["observation_time"].min()) if len(df) else None,
        observation_end=str(df["observation_time"].max()) if len(df) else None,
        notes=(
            "FIRMS detections are not confirmed burned area. Fetched via the FIRMS "
            "area API; key is deliberately omitted from provenance."
        ),
    )
    return df, out_path


def ingest(
    input_dir: Path,
    out_path: Path,
    *,
    settings_obj: Settings = settings,
    is_fixture: bool = False,
) -> tuple[pd.DataFrame, Path]:
    """Ingest FIRMS CSVs from ``input_dir`` into a Parquet dataset."""
    df = read_firms_csvs(
        input_dir,
        available_lag_hours=settings_obj.firms_availability_lag_hours,
        is_fixture=is_fixture,
    )
    from .io import write_parquet
    from .provenance import register_dataset

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(df, out_path, extra_metadata={"dataset": "fire_hotspots"})
    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="fire_hotspots::nasa_firms",
        name="Active fire hotspots (NASA FIRMS)",
        source=str(input_dir),
        license="NASA FIRMS terms (attribution required)",
        treatment="synthetic-fixture" if is_fixture else "real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["observation_time"].min()) if len(df) else None,
        observation_end=str(df["observation_time"].max()) if len(df) else None,
        notes=(
            "SYNTHETIC FIXTURE rows (is_fixture=True) - not observations."
            if is_fixture
            else "FIRMS detections are not confirmed burned area."
        ),
    )
    return df, out_path
