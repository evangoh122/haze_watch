"""CLI integration tests: the full fixture chain and the DuckDB query command."""

import json

import pandas as pd
import pytest

from haze_pipelines.cli import main
from haze_pipelines.fixtures import fixture_polygon_features


def test_query_command_runs_sql_over_parquet(tmp_path, capsys):
    out = tmp_path / "small.parquet"
    pd.DataFrame({"treatment": ["real", "synthetic-fixture", "synthetic-fixture"]}).to_parquet(
        out, index=False
    )
    code = main(
        [
            "query",
            "--file",
            str(out),
            "--sql",
            "SELECT treatment, count(*) AS n FROM dataset GROUP BY treatment ORDER BY treatment",
        ]
    )
    assert code == 0
    printed = capsys.readouterr().out
    assert "real" in printed
    assert "synthetic-fixture" in printed


def test_query_command_without_file_uses_read_parquet(tmp_path, capsys):
    out = tmp_path / "tiny.parquet"
    pd.DataFrame({"n": [3]}).to_parquet(out, index=False)
    escaped = str(out).replace("\\", "/").replace("'", "''")
    code = main(["query", "--sql", f"SELECT sum(n) AS total FROM read_parquet('{escaped}')"])
    assert code == 0
    assert "3" in capsys.readouterr().out


def test_query_spatial_geometry_view(tmp_path, capsys):
    """With the duckdb spatial extension, dataset_geo exposes a GEOMETRY column."""
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect()
    try:
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
    except Exception:  # noqa: BLE001 - any install failure means "spatial unavailable": skip honestly
        pytest.skip("duckdb spatial extension unavailable (offline)")
    finally:
        con.close()

    out = tmp_path / "geoms.parquet"
    pd.DataFrame(
        {
            "polygon_id": ["poly-in", "poly-out"],
            "geometry": [
                "POLYGON ((112.9 -2.1, 113.1 -2.1, 113.1 -1.9, 112.9 -1.9, 112.9 -2.1))",
                "POLYGON ((117.9 -2.1, 118.1 -2.1, 118.1 -1.9, 117.9 -1.9, 117.9 -2.1))",
            ],
        }
    ).to_parquet(out, index=False)

    code = main(
        [
            "query",
            "--file",
            str(out),
            "--sql",
            (
                "SELECT polygon_id FROM dataset_geo "
                "WHERE ST_Intersects(geom, ST_Point(113.0, -2.0)) ORDER BY polygon_id"
            ),
        ]
    )
    assert code == 0
    printed = capsys.readouterr().out
    assert "poly-in" in printed
    assert "poly-out" not in printed


def test_fixture_chain_end_to_end(tmp_path, capsys, monkeypatch):
    """make-fixtures -> ingest -> features -> exposure -> forecast, all on tmp data.

    HAZE_DATA_DIR points at tmp_path so the provenance ledger is written there -
    the committed data/metadata/registry.json must never see test runs.
    """
    monkeypatch.setenv("HAZE_DATA_DIR", str(tmp_path))
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"

    polygons_file = tmp_path / "fixture_polygons.geojson"
    polygons_file.write_text(
        json.dumps({"type": "FeatureCollection", "features": fixture_polygon_features()}),
        encoding="utf-8",
    )

    assert main(["make-fixture-hotspots", "--out-dir", str(raw), "--n", "8"]) == 0
    assert (
        main(
            [
                "ingest-firms",
                "--input",
                str(raw),
                "--out",
                str(processed / "hotspots.parquet"),
                "--fixture",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "ingest-polygons",
                "--input",
                str(polygons_file),
                "--source",
                "FIXTURE",
                "--boundary-type",
                "concession",
                "--license",
                "test",
                "--vintage",
                "2026",
                "--treatment",
                "synthetic-fixture",
                "--out",
                str(processed / "polygons.parquet"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build-features",
                "--polygons",
                str(processed / "polygons.parquet"),
                "--hotspots",
                str(processed / "hotspots.parquet"),
                "--as-of",
                "2026-01-03T00:00:00Z",
                "--out",
                str(processed / "features.parquet"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "run-exposure",
                "--polygons",
                str(processed / "polygons.parquet"),
                "--hotspots",
                str(processed / "hotspots.parquet"),
                "--as-of",
                "2026-01-03T00:00:00Z",
                "--out",
                str(processed / "exposure.parquet"),
                "--out-public",
                str(processed / "exposure_public.geojson"),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "run-forecast",
                "--features",
                str(processed / "features.parquet"),
                "--out",
                str(processed / "forecast.parquet"),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "SYNTHETIC FIXTURE" in out
    assert "not confirmed" in out  # caveat echoed on the exposure run

    # Provenance went to the tmp ledger, never to the repo's data/metadata/.
    ledger = tmp_path / "metadata" / "registry.json"
    assert ledger.exists()
    entries = json.loads(ledger.read_text(encoding="utf-8"))
    assert entries, "CLI runs must register provenance"
    tmp_norm = str(tmp_path).replace("\\", "/")
    assert all(str(e["path"]).replace("\\", "/").startswith(tmp_norm) for e in entries)


def _stations_csv(tmp_path):
    path = tmp_path / "stations.csv"
    pd.DataFrame(
        {"station_id": ["S1"], "label": ["s1"], "latitude": [-2.0], "longitude": [113.0]}
    ).to_csv(path, index=False)
    return path


def test_ingest_weather_cli_runs_without_power_flag(tmp_path, monkeypatch, capsys):
    """ingest-weather must not read the POWER-only --near-real-time-days flag."""
    from haze_pipelines import ingest_weather

    seen: dict = {}

    def fake_ingest(stations, start, end, out, **kwargs):
        seen.update(kwargs)
        return pd.DataFrame({"station_id": ["S1"]}), out

    monkeypatch.setattr(ingest_weather, "ingest_stations", fake_ingest)
    code = main(
        [
            "ingest-weather",
            "--stations",
            str(_stations_csv(tmp_path)),
            "--start",
            "2026-01-01",
            "--end",
            "2026-01-02",
            "--out",
            str(tmp_path / "w.parquet"),
        ]
    )
    assert code == 0
    assert "near_real_time_days" not in seen
    assert "ingested 1 station-days" in capsys.readouterr().out


def test_ingest_power_cli_passes_near_real_time_days(tmp_path, monkeypatch, capsys):
    from haze_pipelines import ingest_power

    seen: dict = {}

    def fake_ingest(stations, start, end, out, **kwargs):
        seen.update(kwargs)
        return pd.DataFrame({"station_id": ["S1"]}), out

    monkeypatch.setattr(ingest_power, "ingest_stations", fake_ingest)
    base = [
        "ingest-power",
        "--stations",
        str(_stations_csv(tmp_path)),
        "--start",
        "2026-01-01",
        "--end",
        "2026-01-02",
        "--out",
        str(tmp_path / "p.parquet"),
    ]
    assert main(base) == 0
    assert seen["near_real_time_days"] == 30.0
    assert main([*base, "--near-real-time-days", "7"]) == 0
    assert seen["near_real_time_days"] == 7.0
    assert "ingested 1 station-days" in capsys.readouterr().out
