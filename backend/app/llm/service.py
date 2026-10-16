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
# Keys are the registry's dataset_id prefixes (before "::"): an id like
# "fire_hotspots::nasa_firms" looks up "fire_hotspots".
_SOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "fire_hotspots": ("hotspot", "fire", "detection", "firms"),
    "weather_observations": ("weather", "rain", "rainfall", "temperature", "wind", "humidity", "drought"),
    "plantation_polygons": ("concession", "polygon", "plantation", "boundary"),
    "exposure": ("exposure", "buffer", "near", "affected"),
    "forecast_baseline": ("forecast", "hazard", "prediction", "probability", "score"),
    "environmental_features": ("feature", "window", "count"),
}


def _hints_for(dataset_id: str) -> tuple[str, ...]:
    """Resolve hints for a registry id; tolerate variants via substring match."""
    key = str(dataset_id).split("::")[0]
    if key in _SOURCE_HINTS:
        return _SOURCE_HINTS[key]
    for family, hints in _SOURCE_HINTS.items():
        if family in str(dataset_id):
            return hints
    return ()


def select_sources(
    messages: list[dict[str, str]], context
) -> list[dict[str, object]]:
    """Return only the registered datasets plausibly used for this question.

    Provenance/inventory questions legitimately use the whole registry; topical
    questions cite matching datasets only. Falls back to an empty list (no
    citation) rather than citing the whole registry for an answer that used none.
    """
    # Only the turn being answered: a keyword in an older turn must not keep
    # citing the full registry for later, unrelated questions.
    question = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
    ).lower()
    if not question:
        return []
    if any(k in question for k in ("dataset", "source", "provenance", "licen", "registered", "loaded")):
        return context.sources
    matched_ids: set[str] = set()
    for dataset_id in (entry.get("dataset_id") or "" for entry in context.registry):
        if any(hint in question for hint in _hints_for(dataset_id)):
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
            # A refused reply cites nothing - it used no source content.
            "sources": [],
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
