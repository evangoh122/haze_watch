# LLM Chat Layer

Grounded, guardrailed analyst chat over the pipeline's own outputs.
Status: **implemented** (API + UI panel + tests). Live LLM calls need a key.

## Providers (OpenAI-compatible)

The client speaks the OpenAI `POST {base_url}/chat/completions` protocol, so any
compatible provider works via environment variables:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` | Notes |
|---|---|---|---|
| **DeepSeek** (default documented) | `https://api.deepseek.com` | a **currently valid** model id from the DeepSeek docs | Model ids rotate over time (e.g. `deepseek-chat` generations get retired); always set `LLM_MODEL` explicitly and check the current API docs. `deepseek-reasoner` exposes chain-of-thought in `reasoning_content`; only `content` is shown to users |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` etc. | |
| Databricks Foundation Model API / Unity Gateway | your workspace OpenAI-compatible URL | served model name | |
| Local vLLM | `http://localhost:8000/v1` | model id | |

Set `LLM_BASE_URL` + `LLM_API_KEY` (see `.env.example`). Without them the
**deterministic fallback** answers from the provenance registry and exposure
summaries only - no network calls, nothing invented - and every reply is labeled
`fallback: true`.

Verify a real provider with the live smoke tests (skipped without credentials):

```bash
LLM_BASE_URL=https://api.deepseek.com LLM_API_KEY=sk-... \
  uv run pytest backend/tests/test_llm_live.py -q
```

## Architecture

```
POST /api/v1/chat
  -> service.chat()
     -> grounding.build_context(LLM_DATA_DIR)   # registry.json + exposure outputs
     -> guardrails.build_messages()             # system rules + dataset context
     -> provider.complete()                     # HTTP or deterministic fallback
     -> guardrails.validate_response()          # flags forbidden claim patterns
  -> {reply, sources, provider, guardrail_flags, disclaimer}
```

- **Grounding**: answers cite registered datasets (`sources[]` includes
  `treatment` = real / real-restricted / synthetic-fixture / derived-unverified).
  Historical runs live in the private HF dataset `egoh33/haze-watch-historical`;
  `scripts/fetch_history_from_hf.py` pulls them into `data/hf_history/`, and
  setting `LLM_DATA_DIR=data/hf_history` makes the agent ground on that history
  (registry + exposure summaries + forecast rows) instead of the local run.
- **Guardrails**: system prompt enforces the data policy (synthetic labeling,
  hotspots != burned area, hazard score != PD, no real-company or causation
  claims); output validation flags patterns like "actuarially validated",
  "guaranteed", numeric PD claims.
- **Disclaimer** is attached to every response and rendered in the UI.
- In Docker, `LLM_DATA_DIR=/data` points grounding at the mounted pipeline
  outputs (see docker-compose.yml).

## UI

Lives in the separate `evangoh-frontend` repo now
(`src/haze-watch/components/chat/ChatPanel.tsx`), routed at `/haze-watch/chat`
there - shows the reply, provenance sources, fallback badge and guardrail
flags.
