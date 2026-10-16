"""LLM chat layer settings (env prefix ``LLM_``).

If ``base_url`` and ``api_key`` are both empty, the service falls back to a
deterministic data-grounded responder so the demo works without credentials and
without fabricating anything.
"""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_", extra="ignore", populate_by_name=True
    )

    # Any OpenAI-compatible endpoint (OpenAI, Databricks Foundation Model API /
    # Unity Gateway, vLLM, ...). Empty => deterministic fallback client.
    base_url: str = ""
    api_key: str = ""
    # Must be a real model id when the HTTP provider is configured (e.g.
    # deepseek-chat); "default" is rejected by most providers.
    model: str = ""

    max_tokens: int = 600
    temperature: float = 0.2
    request_timeout_s: float = 60.0

    # Where the pipeline writes its outputs (context for grounded answers).
    # Accepts LLM_DATA_DIR or the pipeline's HAZE_DATA_DIR; docker-compose mounts
    # ./data at /data and sets LLM_DATA_DIR accordingly.
    data_dir: Path = Field(
        default=Path("data"),
        validation_alias=AliasChoices("LLM_DATA_DIR", "HAZE_DATA_DIR"),
    )


llm_settings = LLMSettings()
