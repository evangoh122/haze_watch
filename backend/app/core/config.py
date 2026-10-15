"""Application configuration loaded from environment variables."""

import json
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: .../<repo>/backend/app/core/config.py -> parents[3].
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )

    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://haze:change-me@localhost:5432/haze_watch"

    # Pipeline outputs served to the dashboards (precomputed; see docs/pipeline.md).
    # Anchored to the repo root, never the process CWD, so the API and its tests behave
    # the same however they are launched. Override with DATA_DIR or HAZE_DATA_DIR
    # (docker-compose mounts the data dir at /data and sets DATA_DIR=/data).
    data_dir: Path = Field(
        default=REPO_ROOT / "data",
        validation_alias=AliasChoices("DATA_DIR", "HAZE_DATA_DIR"),
    )

    # Kept as a plain string so every env format works: a single origin,
    # comma-separated origins, or a JSON array. Use `cors_origins_list` in code.
    cors_origins: str = "http://localhost:5173"

    firms_api_key: str = ""
    open_meteo_url: str = "https://api.open-meteo.com/v1"

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                return [str(origin) for origin in json.loads(raw)]
            except json.JSONDecodeError:
                return []
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
