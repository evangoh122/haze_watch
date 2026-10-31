"""Unit tests: NASA POWER / MERRA-2 weather fallback normalization."""

import pandas as pd

from haze_pipelines.build_features import build_features
from haze_pipelines.config import Settings
from haze_pipelines.fixtures import fixture_hotspots, fixture_polygon_features
from haze_pipelines.ingest_firms import normalize_firms
from haze_pipelines.ingest_polygons import normalize_polygons
from haze_pipelines.ingest_power import ingest_stations, normalize_power_payload
from haze_pipelines.ingest_weather import CANONICAL_COLUMNS
from haze_pipelines.io import read_geo_metadata
from haze_pipelines.provenance import read_registry

POWER_JSON = {
    "geometry": {"coordinates": [116.32, -0.08, 0.0]},
    "properties": {
        "parameter": {
            "T2M_MAX": {"20230101": 31.0, "20230102": 32.0, "20230103": -999.0},
            "PRECTOTCORR": {"20230101": 0.0, "20230102": 5.0, "20230103": -999.0},
            "RH2M": {"20230101": 80.0, "20230102": 75.0, "20230103": -999.0},
            "WS10M_MAX": {"20230101": 3.0, "20230102": 4.0, "20230103": -999.0},
        }
    },
}


def test_normalize_power_payload_maps_missing_and_lag():
    df = normalize_power_payload(
        POWER_JSON,
        "POWER-1",
        availability_lag_hours=48.0,
        fetched_at=pd.Timestamp("2023-01-04", tz="UTC"),
    )

    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 2  # the all-missing tail day is dropped
    first = df.iloc[0]
    assert first["station_id"] == "POWER-1"
    assert first["temperature_max_c"] == 31.0
    assert first["precipitation_sum_mm"] == 0.0
    assert first["wind_max_ms"] == 3.0
    # No verifiable per-value vintage: obs + lag (Jan 3) predates the fetch, so
    # the row is only available at the fetch time.
    assert first["available_time"] == pd.Timestamp("2023-01-04", tz="UTC")


def test_normalize_power_payload_keeps_partial_missing_values():
    payload = {
        "properties": {
            "parameter": {
                "T2M_MAX": {"20230101": 31.0},
                "PRECTOTCORR": {"20230101": -999.0},
                "RH2M": {"20230101": 80.0},
                "WS10M": {"20230101": 3.0},
            }
        }
    }
    df = normalize_power_payload(payload, "POWER-1", latitude=-0.08, longitude=116.32)
    row = df.iloc[0]
    assert row["temperature_max_c"] == 31.0
    assert pd.isna(row["precipitation_sum_mm"])
    assert row["latitude"] == -0.08
    assert row["longitude"] == 116.32


def test_power_ingest_registers_source(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    out = tmp_path / "processed" / "weather.parquet"
    df, written = ingest_stations(
        [{"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}],
        "2023-01-01",
        "2023-01-03",
        out,
        settings_obj=settings_obj,
        client=_FakeClient(POWER_JSON),
        pause_seconds=0,
    )
    assert written == out and len(df) == 2
    entry = {e["dataset_id"]: e for e in read_registry(tmp_path / "metadata")}[
        "weather_observations::nasa_power"
    ]
    assert entry["treatment"] == "real"
    assert "MERRA-2" in entry["name"]
    assert "not ERA5" in entry["notes"]


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(self._payload)

    def close(self) -> None:
        return None


def test_normalize_power_payload_uses_ws10m_max_for_wind():
    payload = {
        "properties": {
            "parameter": {
                "T2M_MAX": {"20230101": 31.0},
                "PRECTOTCORR": {"20230101": 0.0},
                "RH2M": {"20230101": 80.0},
                "WS10M": {"20230101": 99.0},
                "WS10M_MAX": {"20230101": 7.0},
            }
        }
    }
    df = normalize_power_payload(payload, "POWER-1")
    assert df.iloc[0]["wind_max_ms"] == 7.0


class _ParamPowerClient:
    """A POWER client that echoes the requested point and first day."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        params = kwargs.get("params") or {}
        self.calls.append(dict(params))
        day = params["start"]
        return _FakeResponse(
            {
                "geometry": {
                    "coordinates": [params["longitude"], params["latitude"], 0.0]
                },
                "properties": {
                    "parameter": {
                        "T2M_MAX": {day: 31.0},
                        "PRECTOTCORR": {day: 0.0},
                        "RH2M": {day: 80.0},
                        "WS10M_MAX": {day: 5.0},
                    }
                },
            }
        )

    def close(self) -> None:
        return None


def test_power_checkpoint_is_keyed_by_date_range_and_coordinates(tmp_path):
    settings_obj = Settings(data_dir=tmp_path)
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}

    january, _ = ingest_stations(
        [station],
        "2023-01-01",
        "2023-01-02",
        out,
        settings_obj=settings_obj,
        client=_ParamPowerClient(),
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
    )
    assert january["observation_time"].dt.month.unique().tolist() == [1]

    february_client = _ParamPowerClient()
    february, _ = ingest_stations(
        [station],
        "2023-02-01",
        "2023-02-02",
        out,
        settings_obj=settings_obj,
        client=february_client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
    )
    assert february_client.calls, "a new date range must not reuse the January checkpoint"
    assert february["observation_time"].dt.month.unique().tolist() == [2]

    moved = {"station_id": "POWER-1", "latitude": 1.5, "longitude": 118.0}
    moved_client = _ParamPowerClient()
    moved_df, _ = ingest_stations(
        [moved],
        "2023-01-01",
        "2023-01-02",
        out,
        settings_obj=settings_obj,
        client=moved_client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
    )
    assert moved_client.calls, "a new coordinate pair must not reuse the old checkpoint"
    assert moved_df["latitude"].unique().tolist() == [1.5]
    assert len(list(checkpoint_dir.glob("power-*.parquet"))) == 3


def test_power_checkpoint_distinguishes_sub_millidegree_coordinates(tmp_path):
    # A stable station ID must not make two requests below four-decimal
    # precision share a checkpoint and silently return the first point's rows.
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    base = {"station_id": "STABLE", "latitude": -2.00001, "longitude": 113.00001}
    lat_moved = {**base, "latitude": -2.00002}
    lon_moved = {**base, "latitude": -2.00002, "longitude": 113.00002}

    def run(station: dict, client: _ParamPowerClient) -> pd.DataFrame:
        df, _ = ingest_stations(
            [station],
            "2023-01-01",
            "2023-01-02",
            out,
            settings_obj=Settings(data_dir=tmp_path),
            client=client,
            pause_seconds=0,
            checkpoint_dir=checkpoint_dir,
            # availability is max(obs + lag, fetch time)
            clock=lambda: pd.Timestamp("2023-01-03", tz="UTC"),
        )
        return df

    first_client = _ParamPowerClient()
    first = run(base, first_client)
    assert len(first_client.calls) == 1
    assert first["latitude"].unique().tolist() == [-2.00001]
    assert first["longitude"].unique().tolist() == [113.00001]

    lat_client = _ParamPowerClient()
    lat = run(lat_moved, lat_client)
    assert lat_client.calls, "a changed latitude must not reuse the first checkpoint"
    assert lat["latitude"].unique().tolist() == [-2.00002]
    assert lat["longitude"].unique().tolist() == [113.00001]

    lon_client = _ParamPowerClient()
    lon = run(lon_moved, lon_client)
    assert lon_client.calls, "a changed longitude must not reuse the earlier checkpoint"
    assert lon["latitude"].unique().tolist() == [-2.00002]
    assert lon["longitude"].unique().tolist() == [113.00002]

    reuse_client = _ParamPowerClient()
    reused = run(lon_moved, reuse_client)
    assert not reuse_client.calls, "an identical request must reuse its checkpoint"
    assert reused["latitude"].unique().tolist() == [-2.00002]
    assert reused["longitude"].unique().tolist() == [113.00002]
    assert len(list(checkpoint_dir.glob("power-*.parquet"))) == 3


def test_power_checkpoint_is_keyed_by_availability_lag(tmp_path):
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}

    def run(lag: float, client: _ParamPowerClient):
        df, _ = ingest_stations(
            [station],
            "2023-01-01",
            "2023-01-02",
            out,
            settings_obj=Settings(data_dir=tmp_path, weather_availability_lag_hours=lag),
            client=client,
            pause_seconds=0,
            checkpoint_dir=checkpoint_dir,
            # availability is max(obs + lag, fetch time)
            clock=lambda: pd.Timestamp("2023-01-03", tz="UTC"),
        )
        return df

    run(48.0, _ParamPowerClient())
    slower_client = _ParamPowerClient()
    slower = run(72.0, slower_client)
    assert slower_client.calls, "a changed lag must not reuse the old checkpoint"
    gap = slower["available_time"] - slower["observation_time"]
    assert (gap == pd.Timedelta(hours=72)).all()


def test_power_checkpoint_keeps_close_availability_lags_distinct(tmp_path):
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}

    def run(lag: float, client: _ParamPowerClient):
        df, _ = ingest_stations(
            [station],
            "2023-01-01",
            "2023-01-02",
            out,
            settings_obj=Settings(data_dir=tmp_path, weather_availability_lag_hours=lag),
            client=client,
            pause_seconds=0,
            checkpoint_dir=checkpoint_dir,
            # availability is max(obs + lag, fetch time)
            clock=lambda: pd.Timestamp("2023-01-03", tz="UTC"),
        )
        return df

    run(48.00001, _ParamPowerClient())
    second_client = _ParamPowerClient()
    second = run(48.00002, second_client)
    assert second_client.calls, (
        "lags differing below 6 significant digits must not share a checkpoint"
    )
    gap = second["available_time"] - second["observation_time"]
    assert (gap == pd.Timedelta(hours=48.00002)).all()
    assert len(list(checkpoint_dir.glob("power-*.parquet"))) == 2


FETCHED = pd.Timestamp("2026-10-30T12:00:00", tz="UTC")


def _two_day_payload(*days: str) -> dict:
    return {
        "geometry": {"coordinates": [116.32, -0.08, 0.0]},
        "properties": {
            "parameter": {
                name: {day: value for day in days}
                for name, value in (
                    ("T2M_MAX", 31.0),
                    ("PRECTOTCORR", 1.0),
                    ("RH2M", 80.0),
                    ("WS10M_MAX", 4.0),
                )
            }
        },
    }


def test_backfill_row_is_not_available_before_fetch_time():
    df = normalize_power_payload(
        _two_day_payload("20230101"),
        "POWER-1",
        availability_lag_hours=48.0,
        fetched_at=FETCHED,
    )
    # Old behaviour stamped 2023-01-03, letting a 2026-02-01 as_of see values that
    # NASA only served (and may have revised) on the fetch date.
    assert df.iloc[0]["available_time"] == FETCHED


def test_recent_row_also_waits_for_fetch_time():
    # The old 30-day cutoff let a recent row (obs + lag, Oct 27) become visible
    # before the Oct 30 fetch. Without per-value vintage every row waits.
    df = normalize_power_payload(
        _two_day_payload("20261025", "20230101"),
        "POWER-1",
        availability_lag_hours=48.0,
        fetched_at=FETCHED,
    )
    recent = df[df["observation_time"] == pd.Timestamp("2026-10-25", tz="UTC")].iloc[0]
    old = df[df["observation_time"] == pd.Timestamp("2023-01-01", tz="UTC")].iloc[0]
    assert recent["available_time"] == FETCHED
    assert old["available_time"] == FETCHED


def test_availability_is_later_of_observation_plus_lag_and_fetch_time():
    # A huge lag can push obs + lag past the fetch time; the row must keep the
    # later stamp rather than becoming visible before the weather itself exists.
    df = normalize_power_payload(
        _two_day_payload("20261029"),
        "POWER-1",
        availability_lag_hours=240.0,
        fetched_at=FETCHED,
    )
    assert df.iloc[0]["available_time"] == pd.Timestamp("2026-11-08", tz="UTC")


def test_build_features_excludes_backfill_rows_before_fetch_time():
    weather = normalize_power_payload(
        _two_day_payload("20260115"),
        "POWER-1",
        latitude=-2.0,
        longitude=113.0,
        availability_lag_hours=48.0,
        fetched_at=FETCHED,
    )
    polygons = normalize_polygons(
        fixture_polygon_features(),
        source_dataset="FIXTURE",
        boundary_type="concession",
        license="test",
        vintage="2026",
        treatment="synthetic-fixture",
    )[0]
    hot = normalize_firms(
        fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True
    )
    before = build_features(polygons, hot, weather, pd.Timestamp("2026-02-01", tz="UTC"))
    assert before["temp_max_7d_c"].isna().all()
    assert before["weather_station_id"].isna().all()
    # Once the fetch time has passed the same row is visible to the builder.
    after = build_features(polygons, hot, weather, FETCHED + pd.Timedelta(hours=1))
    assert after["weather_station_id"].eq("POWER-1").all()


class _Clock:
    def __init__(self, *times: pd.Timestamp) -> None:
        self._times = list(times)

    def __call__(self) -> pd.Timestamp:
        return self._times.pop(0)


def test_power_checkpoint_cache_hit_preserves_original_fetch_time(tmp_path):
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}
    settings_obj = Settings(data_dir=tmp_path)

    def run(client, clock):
        df, _ = ingest_stations(
            [station],
            "2023-01-01",
            "2023-01-02",
            out,
            settings_obj=settings_obj,
            client=client,
            pause_seconds=0,
            checkpoint_dir=checkpoint_dir,
            clock=clock,
        )
        return df

    first = run(_ParamPowerClient(), _Clock(FETCHED))
    rerun_client = _ParamPowerClient()
    rerun = run(rerun_client, _Clock(FETCHED + pd.Timedelta(days=9)))
    assert not rerun_client.calls, "same rule must hit the checkpoint"
    assert (first["available_time"] == FETCHED).all()
    assert (rerun["available_time"] == FETCHED).all()


class _AdvancingPowerClient:
    """A POWER client whose response mutates the clock, crossing the cutoff."""

    def __init__(self, payload: dict, clock: _Clock, response_time: pd.Timestamp) -> None:
        self._payload = payload
        self._clock = clock
        self._response_time = response_time
        self.calls = 0

    def get(self, url: str, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        self._clock.now = self._response_time
        return _FakeResponse(self._payload)

    def close(self) -> None:
        return None


class _MutableClock:
    def __init__(self, now: pd.Timestamp) -> None:
        self.now = now

    def __call__(self) -> pd.Timestamp:
        return self.now


def test_power_fetch_time_is_captured_after_the_http_response(tmp_path):
    # The request starts just inside the 30-day cutoff; the response arrives just
    # outside it. The row is a backfill row at the response time, so its
    # availability and the persisted fetched_at must be the response time, not
    # the request start.
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}
    request_time = pd.Timestamp("2026-10-30T23:59:59", tz="UTC")
    response_time = pd.Timestamp("2026-10-31T00:00:01", tz="UTC")
    clock = _MutableClock(request_time)
    client = _AdvancingPowerClient(_two_day_payload("20261001"), clock, response_time)

    df, _ = ingest_stations(
        [station],
        "2026-10-01",
        "2026-10-01",
        out,
        settings_obj=Settings(data_dir=tmp_path),
        client=client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
        clock=clock,
    )

    assert client.calls == 1
    assert df.iloc[0]["available_time"] == response_time
    checkpoint = next(checkpoint_dir.glob("power-*.parquet"))
    assert read_geo_metadata(checkpoint)["fetched_at"] == response_time.isoformat()


def test_power_row_inside_old_cutoff_is_not_available_before_fetch_time(tmp_path):
    # Production regression for the fail-closed rule. The observation is 26 days
    # before the fetch, so the old 30-day cutoff classified it as near-real-time
    # and stamped obs + 48h (2026-10-07), leaking a value that NASA may have
    # revised into any as-of between then and the actual fetch.
    checkpoint_dir = tmp_path / "partial"
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -2.0, "longitude": 113.0}
    observed = "2026-10-05"
    fetched = pd.Timestamp("2026-10-31T12:00:00", tz="UTC")

    client = _ParamPowerClient()
    df, _ = ingest_stations(
        [station],
        observed,
        observed,
        out,
        settings_obj=Settings(data_dir=tmp_path),
        client=client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
        clock=_Clock(fetched),
    )

    assert len(client.calls) == 1
    row = df.iloc[0]
    assert row["observation_time"] == pd.Timestamp(observed, tz="UTC")
    assert row["available_time"] == fetched

    checkpoints = list(checkpoint_dir.glob("power-*.parquet"))
    assert len(checkpoints) == 1
    persisted = pd.read_parquet(checkpoints[0])
    assert (persisted["available_time"] == fetched).all()
    assert read_geo_metadata(checkpoints[0])["fetched_at"] == fetched.isoformat()

    polygons = normalize_polygons(
        fixture_polygon_features(),
        source_dataset="FIXTURE",
        boundary_type="concession",
        license="test",
        vintage="2026",
        treatment="synthetic-fixture",
    )[0]
    hot = normalize_firms(
        fixture_hotspots(n=2), source="FIXTURE", available_lag_hours=0.0, is_fixture=True
    )
    before = build_features(polygons, hot, df, pd.Timestamp("2026-10-15", tz="UTC"))
    assert before["temp_max_7d_c"].isna().all()
    assert before["weather_station_id"].isna().all()
    after = build_features(polygons, hot, df, fetched + pd.Timedelta(hours=1))
    assert after["weather_station_id"].eq("POWER-1").all()

    rerun_client = _ParamPowerClient()
    rerun, _ = ingest_stations(
        [station],
        observed,
        observed,
        out,
        settings_obj=Settings(data_dir=tmp_path),
        client=rerun_client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
        clock=_Clock(fetched + pd.Timedelta(days=9)),
    )
    assert not rerun_client.calls, "a cache hit must reuse the fail-closed checkpoint"
    assert rerun.iloc[0]["available_time"] == fetched


def test_power_does_not_reuse_legacy_cutoff_checkpoints(tmp_path):
    # Checkpoints written under the old cutoff rule can contain unsafe
    # obs + lag stamps. The new fail-closed identity must not match them.
    from haze_pipelines.ingest_weather import _coord_token

    checkpoint_dir = tmp_path / "partial"
    checkpoint_dir.mkdir()
    out = tmp_path / "weather.parquet"
    station = {"station_id": "POWER-1", "latitude": -0.08, "longitude": 116.32}
    legacy = checkpoint_dir / (
        "power-POWER-1-"
        f"lat{_coord_token(station['latitude'])}-lon{_coord_token(station['longitude'])}-"
        "20261005-20261005-lag48h-vintage30d.parquet"
    )
    unsafe = normalize_power_payload(
        _two_day_payload("20261005"),
        "POWER-1",
        availability_lag_hours=48.0,
        fetched_at=FETCHED,
    )
    # Reproduce the old cutoff stamp that leaked into earlier as-of builds.
    unsafe["available_time"] = unsafe["observation_time"] + pd.Timedelta(hours=48)
    unsafe.to_parquet(legacy, index=False)

    client = _ParamPowerClient()
    df, _ = ingest_stations(
        [station],
        "2026-10-05",
        "2026-10-05",
        out,
        settings_obj=Settings(data_dir=tmp_path),
        client=client,
        pause_seconds=0,
        checkpoint_dir=checkpoint_dir,
        clock=_Clock(FETCHED),
    )

    assert len(client.calls) == 1, "a legacy cutoff checkpoint must not be reused"
    assert df.iloc[0]["available_time"] == FETCHED
    assert legacy.exists()
    fail_closed = list(checkpoint_dir.glob("power-*-vintagefailclosed.parquet"))
    assert len(fail_closed) == 1
