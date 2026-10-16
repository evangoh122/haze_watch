"""Unit tests: weather normalization from Open-Meteo payloads."""

from datetime import UTC, datetime

from haze_pipelines.ingest_weather import normalize_station_payload

FAKE_PAYLOAD = {
    "latitude": -2.2144,
    "longitude": 113.9186,
    "daily": {
        "time": ["2026-01-01", "2026-01-02"],
        "temperature_2m_max": [33.1, 34.0],
        "precipitation_sum": [10.0, 0.0],
        "relative_humidity_2m_mean": [70, 68],
        "wind_speed_10m_max": [12.0, 9.5],
    },
}


def test_normalize_station_payload_schema_and_lag():
    df = normalize_station_payload(FAKE_PAYLOAD, "STN-1", availability_lag_hours=48.0)
    assert len(df) == 2
    assert df["station_id"].eq("STN-1").all()
    first = df.iloc[0]
    assert first["observation_time"] == datetime(2026, 1, 1, tzinfo=UTC)
    assert first["available_time"] == datetime(2026, 1, 3, tzinfo=UTC)
    assert first["temperature_max_c"] == 33.1


def test_normalize_station_payload_empty_payload():
    df = normalize_station_payload({"latitude": 0, "longitude": 0, "daily": {}}, "STN-2")
    assert df.empty
