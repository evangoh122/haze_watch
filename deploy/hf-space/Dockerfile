# Haze Watch - Hugging Face Space (single container)
#
# NOT DEPLOYED YET - prepared for review. Deployment plan:
#   1. Create Space egoh33/haze-watch (Docker SDK, private first)
#   2. Push this directory as the Space repo root
#   3. Set secrets: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL (DeepSeek), FIRMS_API_KEY
#
# Mirrors the RAG Workbench pattern: nginx serves the built React frontend and
# proxies /api to uvicorn, both managed by supervisord in one container.
#
# Precomputed data note (docs/pipeline.md): the app serves precomputed pipeline
# outputs (Parquet/GeoJSON). No external GIS service is queried per page load.

FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Backend deps + package
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./backend

# Pipeline outputs baked into the image (precomputed exposure layer, registry).
# Real-restricted plantation_polygons.parquet is NOT included - the public layer
# exposure_public.geojson (anonymized, simplified) is the distributable form.
COPY data/processed/exposure_public.geojson /app/data/processed/exposure_public.geojson
COPY data/processed/exposure.summary.json /app/data/processed/exposure.summary.json
COPY data/processed/fire_hotspots.parquet /app/data/processed/fire_hotspots.parquet
COPY data/processed/forecast_baseline.parquet /app/data/processed/forecast_baseline.parquet
COPY data/metadata/registry.json /app/data/metadata/registry.json

# Frontend build + serving config
COPY --from=frontend-build /build/dist /app/frontend/dist
COPY deploy/hf-space/nginx.conf /etc/nginx/nginx.conf
COPY deploy/hf-space/supervisord.conf /etc/supervisord.conf

ENV LLM_DATA_DIR=/app/data

EXPOSE 7860
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
