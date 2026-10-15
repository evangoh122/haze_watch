"""Tests for the chat layer: guardrails, grounding, fallback responder, API."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.llm.config import LLMSettings
from app.llm.grounding import build_context
from app.llm.guardrails import DISCLAIMER, validate_response
from app.llm.provider import DeterministicFallbackClient
from app.llm.service import chat
from app.main import app


def _write_ledger(data_dir: Path) -> None:
    import json

    metadata = data_dir / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "registry.json").write_text(
        json.dumps(
            [
                {
                    "dataset_id": "fire_hotspots::nasa_firms",
                    "name": "hotspots",
                    "source": "fixture",
                    "license": "NASA FIRMS terms",
                    "treatment": "synthetic-fixture",
                    "path": "data/processed/fire_hotspots.parquet",
                    "row_count": 40,
                }
            ]
        ),
        encoding="utf-8",
    )


# --- guardrails ---------------------------------------------------------


def test_validate_response_flags_forbidden_claims():
    flags = validate_response("This is an actuarially validated premium that guarantees returns.")
    assert "actuarially validated claim" in flags
    assert "guarantee claim" in flags


def test_validate_response_passes_compliant_reply():
    flags = validate_response(
        "The exposure summary shows 5 polygons with detections. These are synthetic data."
    )
    assert flags == []


# --- grounding -----------------------------------------------------------


def test_grounding_cites_registered_datasets(tmp_path):
    _write_ledger(tmp_path)
    context = build_context(tmp_path)
    assert any(s["dataset_id"] == "fire_hotspots::nasa_firms" for s in context.sources)
    assert "fire_hotspots::nasa_firms" in context.text


def test_grounding_states_missing_registry_honestly(tmp_path):
    context = build_context(tmp_path)
    assert "NO DATASETS REGISTERED" in context.text
    assert context.sources == []


# --- service + fallback ---------------------------------------------------


def test_service_returns_grounded_fallback_with_disclaimer(tmp_path):
    _write_ledger(tmp_path)
    settings_obj = LLMSettings(data_dir=tmp_path)  # no base_url/api_key => fallback
    result = chat(
        [{"role": "user", "content": "What datasets are loaded?"}],
        client=DeterministicFallbackClient(),
        settings_obj=settings_obj,
    )
    assert result["fallback"] is True
    assert result["provider"] == "deterministic-fallback"
    assert result["disclaimer"] == DISCLAIMER
    assert "fire_hotspots::nasa_firms" in result["reply"]
    assert result["guardrail_flags"] == []
    assert result["sources"][0]["treatment"] == "synthetic-fixture"


def test_fallback_never_claims_pd_or_burned_area(tmp_path):
    _write_ledger(tmp_path)
    settings_obj = LLMSettings(data_dir=tmp_path)
    for question in ("What is the probability of default?", "Which areas burned?"):
        result = chat(
            [{"role": "user", "content": question}],
            client=DeterministicFallbackClient(),
            settings_obj=settings_obj,
        )
        assert result["guardrail_flags"] == [], question


# --- API ------------------------------------------------------------------


def test_chat_endpoint_end_to_end():
    client = TestClient(app)
    response = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "What datasets are loaded?"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"] == DISCLAIMER
    assert body["reply"]
    assert "fallback" in body
    assert isinstance(body["sources"], list)


def test_chat_endpoint_validates_input():
    client = TestClient(app)
    assert client.post("/api/v1/chat", json={"messages": []}).status_code == 422
    assert (
        client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": ""}]},
        ).status_code
        == 422
    )
