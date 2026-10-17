# Haze Watch - Hugging Face Space (backend-only)
#
# The frontend moved to evangoh-frontend (which bundles its own copy of the
# Haze Watch app, imported during the evangoh.com frontend split). This
# Space now serves only the API, reached in production via the Cloudflare
# Worker's /haze-watch/api* rule (see deploy/cloudflare/) which strips the
# /haze-watch prefix before forwarding here.
#
# Build context is the PROJECT REPO ROOT (paths below are repo-root
# relative: backend/, data/). For the Space, push the repo root as the
# Space repo root with this file at /Dockerfile, or test locally with:
#     docker build -f deploy/hf-space/Dockerfile .
#
# Set secrets: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL (DeepSeek), FIRMS_API_KEY
#
# Precomputed data note (docs/pipeline.md): the app serves precomputed pipeline
# outputs (Parquet/GeoJSON). No external GIS service is queried per page load.

FROM python:3.12-slim
WORKDIR /app

# Backend deps + package
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./backend

# Pipeline outputs baked into the image (precomputed exposure layer, registry).
# NOTE: these are gitignored, so the processed files must exist before building -
# run the pipeline first (make ingest-firms / ingest-weather / build-features /
# run-exposure) or copy them in. Real-restricted plantation_polygons.parquet is
# NOT included - the public layer exposure_public.geojson (anonymized,
# simplified) is the distributable form.
COPY data/processed/exposure_public.geojson /app/data/processed/exposure_public.geojson
COPY data/processed/exposure.summary.json /app/data/processed/exposure.summary.json
COPY data/processed/fire_hotspots.parquet /app/data/processed/fire_hotspots.parquet
COPY data/processed/forecast_baseline.parquet /app/data/processed/forecast_baseline.parquet
COPY data/metadata/registry.json /app/data/metadata/registry.json

# config.py reads DATA_DIR (or HAZE_DATA_DIR) — the deployed Space also sets
# this itself via its own Settings -> Variables, which is what's actually
# load-bearing in production; this ENV just makes a local `docker run` work
# without extra flags.
ENV DATA_DIR=/app/data

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
