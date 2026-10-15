"""Chat providers: OpenAI-compatible HTTP client + deterministic data-grounded fallback.

The fallback answers only from the grounded dataset context - it never invents
figures - so the demo works with no LLM credentials and stays auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import LLMSettings, llm_settings
from .grounding import GroundedContext


@dataclass
class ChatResult:
    content: str
    model: str
    provider: str
    fallback: bool = False
    usage: dict[str, Any] = field(default_factory=dict)


class ChatClient(Protocol):
    name: str

    def complete(self, messages: list[dict], context: GroundedContext, settings: LLMSettings) -> ChatResult: ...


class OpenAICompatibleClient:
    """POST {base_url}/chat/completions with an OpenAI-compatible payload."""

    name = "openai-compatible"

    def __init__(self, client: Any | None = None):
        self._client = client

    def complete(self, messages: list[dict], context: GroundedContext, settings: LLMSettings) -> ChatResult:
        import httpx

        own_client = self._client is None
        client = self._client or httpx.Client(timeout=settings.request_timeout_s)
        try:
            response = client.post(
                settings.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.api_key}"},
                json={
                    "model": settings.model,
                    "messages": messages,
                    "max_tokens": settings.max_tokens,
                    "temperature": settings.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
        finally:
            if own_client:
                client.close()

        content = data["choices"][0]["message"]["content"]
        return ChatResult(
            content=content,
            model=data.get("model", settings.model),
            provider=self.name,
            usage=data.get("usage", {}),
        )


class DeterministicFallbackClient:
    """Answers from pipeline outputs only; clearly labeled as not an LLM."""

    name = "deterministic-fallback"

    def complete(self, messages: list[dict], context: GroundedContext, settings: LLMSettings) -> ChatResult:
        question = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        answer = answer_from_context(question, context)
        return ChatResult(content=answer, model="none (deterministic)", provider=self.name, fallback=True)


def answer_from_context(question: str, context: GroundedContext) -> str:
    """Template an answer strictly from the grounded context."""
    q = question.lower()
    summary = context.summary or {}
    label = "Answer from loaded pipeline data (deterministic fallback - no LLM connected)."

    if not context.registry and not summary:
        return (
            f"{label} No processed datasets are registered yet, so I cannot answer "
            f"'{question}'. Run the ingestion pipeline first (see docs/pipeline.md)."
        )

    if any(k in q for k in ("dataset", "source", "provenance", "licen", "data do you have")):
        lines = [label, "Registered datasets:"]
        for entry in context.registry:
            lines.append(
                f"- {entry.get('dataset_id')} (treatment={entry.get('treatment')}, "
                f"rows={entry.get('row_count')}, license={entry.get('license')})"
            )
        return "\n".join(lines)

    if any(k in q for k in ("hotspot", "detection", "fire", "exposure", "polygon", "concession", "how many")):
        if not summary:
            return f"{label} No exposure summary is loaded, so I cannot report fire exposure figures."
        lines = [
            f"{label} Exposure summary (as_of={summary.get('as_of')}):",
            f"- {summary.get('polygons')} polygons, {summary.get('hotspots_considered')} hotspot detections considered",
            f"- {summary.get('polygons_with_detections')} polygons have detections within {summary.get('buffer_km')} km",
            f"- polygon treatment={summary.get('polygon_treatment')}, hotspot treatment={summary.get('hotspot_treatment')}",
            f"- caveat: {summary.get('caveat', 'n/a')}",
        ]
        if summary.get("warning"):
            lines.append(f"- WARNING: {summary['warning']}")
        return "\n".join(lines)

    if any(k in q for k in ("forecast", "hazard", "risk score", "predict", "probability")):
        return (
            f"{label} The loaded forecast is a deterministic baseline hazard score "
            "(0-1), not a calibrated probability, not a validated fire forecast and "
            "not a probability of default. ML models arrive in Phase 2 - no "
            "predictive accuracy is claimed today."
        )

    if any(k in q for k in ("company", "financial", "borrower", "credit", "insurance", "ebitda", "loan")):
        return (
            f"{label} All companies, financial statements, bank exposures and "
            "insurance policies in this platform are ENTIRELY SYNTHETIC and "
            "fictional. The synthetic financial data engine is not yet loaded in "
            "this deployment; when it is, every figure will be labeled synthetic. "
            "No credit-rating or insurance-pricing conclusions can be drawn."
        )

    if any(k in q for k in ("peat", "weather", "land cover", "mapbiomas")):
        return (
            f"{label} Weather observations are real (Open-Meteo/ERA5 reanalysis). "
            "Peatland layers are available from the GFW ArcGIS service "
            "(fetch-concessions --source gfw-peatlands) but were not ingested in "
            "this deployment. See data/metadata/registry.json for what is loaded."
        )

    return (
        f"{label} I can answer questions about: registered datasets and their "
        "provenance/licensing, fire hotspot exposure over concession polygons, the "
        "baseline hazard score, weather inputs, and the synthetic-data policy. "
        "Ask about one of those, or connect an LLM (LLM_BASE_URL + LLM_API_KEY) for "
        "free-form analysis."
    )


def make_client(settings: LLMSettings | None = None) -> ChatClient:
    """Pick the provider: HTTP client when configured, deterministic fallback otherwise."""
    settings = settings or llm_settings
    if settings.base_url and settings.api_key:
        return OpenAICompatibleClient()
    return DeterministicFallbackClient()
