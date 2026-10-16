"""Unit tests for chat source selection, answer routing, and refusal behavior.

Regression coverage for review findings: _SOURCE_HINTS keys must match the
registry's dataset_id prefixes, source selection must use only the current
turn, forecast questions must reach the forecast answer, and a guardrail
refusal must not attach sources.
"""

from __future__ import annotations

from app.llm.grounding import GroundedContext
from app.llm.provider import ChatResult, answer_from_context
from app.llm.service import _hints_for, select_sources

REGISTRY = [
    {"dataset_id": "fire_hotspots::nasa_firms"},
    {"dataset_id": "weather_observations::open_meteo"},
    {"dataset_id": "plantation_polygons::BNPB_GlobalForestWatch2"},
    {"dataset_id": "environmental_features::2026-02-01"},
    {"dataset_id": "exposure::2026-02-01"},
    {"dataset_id": "forecast_baseline::0.1.0"},
]


def _context() -> GroundedContext:
    sources = [{"dataset_id": e["dataset_id"]} for e in REGISTRY]
    summary = {
        "as_of": "2026-02-01",
        "polygons": 300,
        "hotspots_considered": 40,
        "polygons_with_detections": 5,
        "buffer_km": 10,
        "polygon_treatment": "real-restricted",
        "hotspot_treatment": "synthetic-fixture",
        "caveat": "hotspot counts are detections",
    }
    return GroundedContext(text="", sources=sources, summary=summary, registry=REGISTRY)


def test_hints_resolve_every_registry_prefix():
    for entry in REGISTRY:
        assert _hints_for(entry["dataset_id"]), f"no hints resolve for {entry['dataset_id']}"


def test_sources_match_the_question():
    picked = select_sources(
        [{"role": "user", "content": "how many hotspot detections are near concessions?"}],
        _context(),
    )
    ids = {s["dataset_id"] for s in picked}
    assert "fire_hotspots::nasa_firms" in ids
    assert "forecast_baseline::0.1.0" not in ids


def test_only_the_current_turn_selects_sources():
    """A past 'datasets' question must not keep returning the full registry."""
    messages = [
        {"role": "user", "content": "what datasets and sources do you have?"},
        {"role": "assistant", "content": "Registered datasets: ..."},
        {"role": "user", "content": "hotspot detections"},
    ]
    picked = select_sources(messages, _context())
    assert {s["dataset_id"] for s in picked} == {"fire_hotspots::nasa_firms"}


def test_forecast_question_reaches_forecast_answer():
    answer = answer_from_context("what is the fire forecast?", _context())
    assert "Exposure summary" not in answer
    assert "hazard score" in answer


def test_refused_reply_has_no_sources(monkeypatch):
    from app.llm import service

    class StubClient:
        name = "stub"

        def complete(self, messages, context, settings):
            return ChatResult(content="stub reply", model="stub-model", provider="stub", fallback=False)

    monkeypatch.setattr(service, "validate_response", lambda content: ["made_up_statistic"])
    result = service.chat(
        [{"role": "user", "content": "fire forecast"}],
        client=StubClient(),
        settings_obj=service.llm_settings,
    )
    assert result["guardrail_flags"] == ["made_up_statistic"]
    assert result["sources"] == []
