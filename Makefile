.PHONY: setup up down test lint ingest-firms ingest-firms-api ingest-weather

setup:
	uv sync --all-packages
	cd frontend && npm install

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
	cd frontend && npm run typecheck
	cd frontend && npm test

lint:
	uv run ruff check backend ml pipelines synthetic private scripts
	cd frontend && npm run lint

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

# Synthetic financial engine is not implemented yet; `synthetic/` contains
# stubs and skipped placeholder tests only. See README status table.
