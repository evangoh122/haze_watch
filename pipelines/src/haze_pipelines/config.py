"""Pipeline configuration.

Paths default to the repository ``data/`` directory and can be overridden per run
via CLI flags or environment variables (HAZE_DATA_DIR).
"""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAZE_", extra="ignore")

    data_dir: Path = Path("data")

    # NASA FIRMS API key (https://firms.modaps.eosdis.nasa.gov/api/). Empty = no fetch.
    # Accepts both HAZE_FIRMS_API_KEY and the backend's FIRMS_API_KEY name.
    firms_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("HAZE_FIRMS_API_KEY", "FIRMS_API_KEY"),
    )

    # Open-Meteo historical (ERA5 reanalysis) API - public, no key required.
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"

    # Assumed latency between an observation and its public availability.
    # Used for point-in-time correctness; see docs/pipeline.md.
    firms_availability_lag_hours: float = 3.0
    weather_availability_lag_hours: float = 48.0

    # Spatial defaults (WGS84).
    crs: str = "EPSG:4326"
    exposure_radius_km: float = 25.0
    # Beyond this distance a weather station no longer represents a polygon.
    weather_max_distance_km: float = 300.0

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def synthetic_dir(self) -> Path:
        return self.data_dir / "synthetic"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"


settings = Settings()
