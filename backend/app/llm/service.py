"""Chat service: grounding + guardrails + provider orchestration.

Every reply is built from the pipeline's own outputs (provenance registry,
exposure summaries), passed through guardrail validation, and returned with its
sources and the research disclaimer. With no LLM credentials configured the
deterministic fallback answers from data only - nothing is ever invented.
"""

from __future__ import annotations

from typing import Any

from .config import LLMSettings, llm_settings
from .grounding import build_context
from .guardrails import DISCLAIMER, build_messages, validate_response
from .provider import ChatClient, make_client


def chat(
    messages: list[dict[str, str]],
    *,
    client: ChatClient | None = None,
    settings_obj: LLMSettings | None = None,
) -> dict[str, Any]:
    """Run one chat turn. ``messages`` are ``{"role", "content"}`` dicts."""
    settings_obj = settings_obj or llm_settings
    client = client or make_client(settings_obj)

    context = build_context(settings_obj.data_dir)
    provider_messages = build_messages(messages, context.text)
    result = client.complete(provider_messages, context, settings_obj)

    return {
        "reply": result.content,
        "sources": context.sources,
        "model": result.model,
        "provider": result.provider,
        "fallback": result.fallback,
        "guardrail_flags": validate_response(result.content),
        "disclaimer": DISCLAIMER,
    }
