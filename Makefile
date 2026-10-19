.PHONY: setup up down test lint ingest-firms ingest-firms-api ingest-weather coverage-stations ingest-weather-full ingest-haze

setup:
	uv sync --all-packages

up:
	docker compose up --build

down:
	docker compose down

test:
	uv run python scripts/check_data_not_tracked.py
	uv run pytest backend/tests
	uv run pytest pipelines/tests
	uv run pytest synthetic/tests
	uv run pytest private/tests

lint:
	uv run ruff check backend ml pipelines synthetic private scripts

# Weather window for the ingest-weather target (override: make ingest-weather START=... END=...)
START ?= 2026-01-01
END ?= 2026-01-31

ingest-firms:
	uv run haze-pipelines ingest-firms --input data/raw/firms --out data/processed/fire_hotspots.parquet

# Automatic pull from the NASA FIRMS API (needs FIRMS_API_KEY / HAZE_FIRMS_API_KEY).
# Override the window: make ingest-firms-api FIRMS_DAYS=5
FIRMS_DAYS ?= 3
ingest-firms-api:
	uv run haze-pipelines ingest-firms --from-api --days $(FIRMS_DAYS) --out data/processed/fire_hotspots.parquet

ingest-weather:
	uv run haze-pipelines ingest-weather --stations data/raw/stations.csv --start $(START) --end $(END) --out data/processed/weather.parquet

# Full-depth panels over the concession region (110-120E, 4S-6N).
WEATHER_START ?= 1981-01-01
WEATHER_END ?= 2026-10-17
HAZE_START ?= 2022-08-31
HAZE_END ?= 2026-10-18

coverage-stations:
	uv run python scripts/make_coverage_stations.py \
		--polygons data/processed/plantation_polygons.parquet \
		--k 5 --out data/raw/weather/coverage_5.csv

ingest-weather-full:
	uv run haze-pipelines ingest-power --stations data/raw/weather/coverage_5.csv \
		--start $(WEATHER_START) --end $(WEATHER_END) --pause 1 --retries 5 \
		--checkpoint-dir data/interim/weather_partial \
		--out data/processed/weather.parquet

ingest-haze:
	uv run haze-pipelines ingest-aerosol --bbox 110,-4,120,6 --grid 11 \
		--start $(HAZE_START) --end $(HAZE_END) --pause 1 --retries 5 \
		--out data/processed/haze_aerosol.parquet

# Synthetic financial engine is not implemented yet; `synthetic/` contains
# stubs and skipped placeholder tests only. See README status table.
