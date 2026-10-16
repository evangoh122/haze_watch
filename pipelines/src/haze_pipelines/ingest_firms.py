"""NASA FIRMS active-fire hotspot ingestion.

Accepts FIRMS CSV exports (MODIS or VIIRS column layouts) from ``data/raw/firms/``
or fetches an area extract from the FIRMS API when ``FIRMS_API_KEY`` is configured.

Real observations only: any fixture data must be generated via
``haze_pipelines.fixtures`` and is labeled ``is_fixture=True``.
"""

from __future__ import annotations

import hashlib
import time
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

    if len(df) == 0:
        # Empty windows (e.g. plain-text API notices) skip the transforms below -
        # empty object-dtype columns break the timestamp string concat. Datetime
        # columns must carry a real dtype: pd.concat with empty object frames
        # otherwise coerces real rows to object and breaks .dt downstream.
        empty = pd.DataFrame(columns=CANONICAL_COLUMNS)
        empty["observation_time"] = pd.Series(dtype="datetime64[ns, UTC]")
        empty["available_time"] = pd.Series(dtype="datetime64[ns, UTC]")
        return empty

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


# The exact plain-text notices the FIRMS area API returns for a window with no
# detections. Anything else that is not CSV is an error, not an empty window.
_EMPTY_WINDOW_NOTICES = {"no hotspots available", "no data available"}

# FIRMS area API window limit per request (the API form documents 1-5 days;
# larger DAY_RANGE values consume multiple transactions and are rejected by the
# form). Longer spans are chunked by fetch_firms_range.
MAX_DAYS_PER_REQUEST = 5


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter (shared-key bursts must not synchronize)."""
    import random

    return min(30.0, 2.0**attempt) * (0.5 + random.random())


def fetch_firms_area(
    area: str,
    days: int,
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    sensor: str = "MODIS_NRT",
    date: str | None = None,
    max_retries: int = 4,
    sleep=time.sleep,
) -> pd.DataFrame:
    """Fetch an area extract from the FIRMS CSV API (requires FIRMS_API_KEY).

    ``area`` is ``west,south,east,north`` (a WGS84 bounding box) and ``days`` the
    window length (1-5 per request). ``date`` (``YYYY-MM-DD``) anchors the window
    at that day (returns DATE .. DATE+days-1); without it the API returns the
    trailing window ending today. See https://firms.modaps.eosdis.nasa.gov/api/area/.
    """
    from datetime import date as date_cls

    key = api_key if api_key is not None else settings.firms_api_key
    if not key:
        raise RuntimeError(
            "FIRMS API key not configured. Set FIRMS_API_KEY (alias "
            "HAZE_FIRMS_API_KEY) for automatic pulls, or place CSV exports in "
            "data/raw/firms/ and ingest without --from-api."
        )
    if days < 1 or days > MAX_DAYS_PER_REQUEST:
        raise ValueError(
            f"FIRMS area API supports 1-{MAX_DAYS_PER_REQUEST} days per request "
            "(chunk longer spans with fetch_firms_range / --start-date --backfill-days)"
        )
    if date is not None:
        date_cls.fromisoformat(date)  # raises ValueError on malformed dates

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{sensor}/{area}/{days}"
    if date is not None:
        url += f"/{date}"
    own_client = client is None
    client = client or httpx.Client(timeout=60.0)
    try:
        body = ""
        status = 0
        for attempt in range(max_retries):
            try:
                response = client.get(url)
            except httpx.TransportError:
                if attempt == max_retries - 1:
                    raise
                if sleep is not None:
                    sleep(_backoff_seconds(attempt))
                continue
            status = response.status_code
            # Read the body BEFORE judging the status: FIRMS explains failures
            # (and empty windows) in a short plain-text notice that never
            # contains the key. HTTP 400 has proven transient (shared-key
            # bursts), so 4xx/5xx retry with backoff + jitter.
            body = (response.text or "").strip()
            if status < 400:
                break
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"FIRMS API HTTP {status} ({sensor}, {days}-day window from "
                    f"{date or 'today'}): {body[:200]}"
                )
            if sleep is not None:
                sleep(_backoff_seconds(attempt))
    finally:
        if own_client:
            client.close()

    from io import StringIO

    body = (response.text or "").strip()
    first_line = body.splitlines()[0].lower() if body else ""
    if "latitude" not in first_line:
        # Only the known empty-window notices mean "no detections". Anything
        # else (service notices, auth failures) must fail loudly - a 25-year
        # backfill may never silently omit a window. Never interpolate the
        # request URL here: it contains the MAP_KEY and the CLI prints
        # RuntimeError messages to stderr (CI logs).
        if body.lower().rstrip(".") in _EMPTY_WINDOW_NOTICES:
            return normalize_firms(
                pd.DataFrame(
                    columns=[
                        "latitude",
                        "longitude",
                        "acq_date",
                        "acq_time",
                        "satellite",
                        "confidence",
                        "frp",
                        "daynight",
                        "bright_ti4",
                    ]
                ),
                source=f"NASA_FIRMS_{sensor}",
                available_lag_hours=settings.firms_availability_lag_hours,
            )
        raise RuntimeError(
            f"FIRMS API error ({sensor}, {days}-day window from {date or 'today'}): {body[:200]}"
        )

    return normalize_firms(
        pd.read_csv(StringIO(body)),
        source=f"NASA_FIRMS_{sensor}",
        available_lag_hours=settings.firms_availability_lag_hours,
    )


def fetch_firms_range(
    area: str,
    start_date: str,
    backfill_days: int,
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    sensor: str = "MODIS_NRT",
    window_days: int = MAX_DAYS_PER_REQUEST,
    sleep=time.sleep,
    progress=None,
) -> pd.DataFrame:
    """Fetch a historical range by walking the area API in ``window_days`` chunks.

    The area API takes ``DAY_RANGE`` + ``DATE`` (returns DATE..DATE+DAY_RANGE-1),
    so a range is one request per window. Rows are deduplicated across windows on
    ``hotspot_id`` (stable hash of source/lat/lon/time), so overlapping or retried
    windows never double-count a detection. Gentle pacing between requests keeps
    well inside the MAP_KEY quota (5,000 transactions / 10 min).
    """
    from datetime import date as date_cls
    from datetime import timedelta

    if backfill_days < 1:
        raise ValueError("backfill_days must be >= 1")
    if window_days < 1 or window_days > MAX_DAYS_PER_REQUEST:
        raise ValueError(f"window_days must be 1-{MAX_DAYS_PER_REQUEST}")
    start = date_cls.fromisoformat(start_date)

    frames: list[pd.DataFrame] = []
    offset = 0
    from datetime import date as date_cls

    today = date_cls.today()
    while offset < backfill_days:
        window_date = start + timedelta(days=offset)
        if window_date > today:
            if progress is not None:
                progress(f"firms range stops at today ({today}); skipping future windows")
            break
        # The window must not extend past today: the API is asked for
        # DATE..DATE+span-1, so clamp the span to the remaining days.
        span = min(window_days, backfill_days - offset, (today - window_date).days + 1)
        window_start = window_date.isoformat()
        if progress is not None:
            progress(f"firms window {window_start} +{span}d ({sensor})")
        frames.append(
            fetch_firms_area(
                area,
                span,
                api_key=api_key,
                client=client,
                sensor=sensor,
                date=window_start,
                sleep=sleep,
            )
        )
        offset += span
        if offset < backfill_days and sleep is not None:
            sleep(0.25)

    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    if len(merged):
        # Defensive: mixed empty/data windows must not leave object-dtype times
        # (the sync groups by observation_time.dt.year).
        merged["observation_time"] = pd.to_datetime(
            merged["observation_time"], utc=True, errors="coerce"
        )
        merged["available_time"] = pd.to_datetime(
            merged["available_time"], utc=True, errors="coerce"
        )
    return merged.drop_duplicates(subset=["hotspot_id"]).reset_index(drop=True)


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
    start_date: str | None = None,
    backfill_days: int | None = None,
    settings_obj: Settings = settings,
    client: httpx.Client | None = None,
    progress=None,
) -> tuple[pd.DataFrame, Path]:
    """Automatic pull: fetch FIRMS detections and persist them.

    Requires a free FIRMS MAP_KEY (``FIRMS_API_KEY`` / ``HAZE_FIRMS_API_KEY``).
    Trailing mode: the last ``days`` days (1-5). Historical mode: pass
    ``start_date`` + ``backfill_days`` to walk ``[start_date, start_date+backfill_days)``
    in <=5-day windows (``backfill_days`` alone = that many days ending today).
    Registered with treatment ``real`` - never ``synthetic-fixture``.
    """
    from datetime import date as date_cls
    from datetime import timedelta

    resolved_area = area or default_area()
    if start_date is not None or backfill_days is not None:
        if backfill_days is None:
            raise ValueError("backfill_days is required with start_date")
        if start_date is None:
            start_date = (date_cls.today() - timedelta(days=backfill_days - 1)).isoformat()
        df = fetch_firms_range(
            resolved_area,
            start_date,
            backfill_days,
            api_key=settings_obj.firms_api_key,
            client=client,
            sensor=sensor,
            progress=progress,
        )
        window_desc = f"start={start_date}, backfill_days={backfill_days} (chunked <=5d windows)"
    else:
        df = fetch_firms_area(
            resolved_area,
            days,
            api_key=settings_obj.firms_api_key,
            client=client,
            sensor=sensor,
        )
        window_desc = f"trailing days={days}"

    from .io import write_parquet
    from .provenance import register_dataset

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_parquet(
        df,
        out_path,
        extra_metadata={
            "dataset": "fire_hotspots",
            "source": f"NASA_FIRMS API ({sensor})",
            "processing": "NRT",
        },
    )
    register_dataset(
        settings_obj.metadata_dir,
        dataset_id="fire_hotspots::nasa_firms",
        name="Active fire hotspots (NASA FIRMS)",
        source=f"NASA FIRMS area API (sensor={sensor}, area={resolved_area}, {window_desc})",
        license="NASA FIRMS terms (attribution required)",
        treatment="real",
        path=out_path,
        row_count=len(df),
        observation_start=str(df["observation_time"].min()) if len(df) else None,
        observation_end=str(df["observation_time"].max()) if len(df) else None,
        notes=(
            "FIRMS detections are not confirmed burned area. Fetched via the FIRMS "
            "area API (NRT - near-real-time processing). For Standard Processing "
            "(SP) archive quality use the FIRMS Archive Download Tool CSVs with "
            "ingest-firms --input. Key is deliberately omitted from provenance."
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
