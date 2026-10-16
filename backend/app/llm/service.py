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

# Keyword hints per dataset family, used to cite only the sources an answer used.
_SOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "fire": ("hotspot", "fire", "detection", "firms"),
    "weather": ("weather", "rain", "rainfall", "temperature", "wind", "humidity", "drought"),
    "plantation": ("concession", "polygon", "plantation", "boundary"),
    "exposure": ("exposure", "buffer", "near", "affected"),
    "forecast": ("forecast", "hazard", "prediction", "probability", "score"),
    "environmental_features": ("feature", "window", "count"),
}


def select_sources(
    messages: list[dict[str, str]], context
) -> list[dict[str, object]]:
    """Return only the registered datasets plausibly used for this question.

    Provenance/inventory questions legitimately use the whole registry; topical
    questions cite matching datasets only. Falls back to an empty list (no
    citation) rather than citing the whole registry for an answer that used none.
    """
    question = " ".join(m.get("content", "") for m in messages if m.get("role") == "user").lower()
    if not question:
        return []
    if any(k in question for k in ("dataset", "source", "provenance", "licen", "registered", "loaded")):
        return context.sources
    matched_ids: set[str] = set()
    for dataset_id in (entry.get("dataset_id") or "" for entry in context.registry):
        key = str(dataset_id).split("::")[0]
        hints = _SOURCE_HINTS.get(key, ())
        if any(hint in question for hint in hints):
            matched_ids.add(str(dataset_id))
    return [s for s in context.sources if s.get("dataset_id") in matched_ids]


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

    flags = validate_response(result.content)
    if flags:
        # A flagged reply must never reach the user, even from a live provider.
        return {
            "reply": (
                "I can't provide that answer: the response violated the platform's "
                f"data policy ({', '.join(flags)}). Hazard scores are not probabilities "
                "of default, hotspot detections are not confirmed burned area or "
                "causation, and all commercial data is synthetic."
            ),
            "sources": select_sources(messages, context),
            "model": result.model,
            "provider": result.provider,
            "fallback": result.fallback,
            "guardrail_flags": flags,
            "disclaimer": DISCLAIMER,
        }

    return {
        "reply": result.content,
        "sources": select_sources(messages, context),
        "model": result.model,
        "provider": result.provider,
        "fallback": result.fallback,
        "guardrail_flags": flags,
        "disclaimer": DISCLAIMER,
    }
