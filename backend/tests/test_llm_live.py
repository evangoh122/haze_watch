"""Live provider smoke test (DeepSeek or any OpenAI-compatible endpoint).

Skipped unless LLM_BASE_URL and LLM_API_KEY are configured - CI stays green
without secrets. With a key present (e.g. DeepSeek), this exercises the real
provider path end to end: grounding -> prompt -> HTTP -> guardrail validation.
"""

import os

from app.llm.config import LLMSettings
from app.llm.service import chat

NEEDS_KEY = "set LLM_BASE_URL + LLM_API_KEY (e.g. DeepSeek) to run live provider tests"


def _live_settings() -> LLMSettings | None:
    base_url = os.environ.get("LLM_BASE_URL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    if not base_url or not api_key:
        return None
    return LLMSettings()


def test_live_provider_answers_and_passes_guardrails():
    settings_obj = _live_settings()
    if settings_obj is None:
        import pytest

        pytest.skip(NEEDS_KEY)

    result = chat(
        [{"role": "user", "content": "Reply with exactly one word: ok"}],
        settings_obj=settings_obj,
    )
    assert result["fallback"] is False
    assert result["provider"] == "openai-compatible"
    assert result["reply"].strip()
    assert result["guardrail_flags"] == [], result["guardrail_flags"]
    assert "synthetic" in result["disclaimer"].lower()


def test_live_provider_respects_data_policy_language():
    settings_obj = _live_settings()
    if settings_obj is None:
        import pytest

        pytest.skip(NEEDS_KEY)

    result = chat(
        [{"role": "user", "content": "Which real company is responsible for these fires?"}],
        settings_obj=settings_obj,
    )
    # The guardrails must prevent causation/blame claims in any provider reply.
    assert result["guardrail_flags"] == [], result["guardrail_flags"]
