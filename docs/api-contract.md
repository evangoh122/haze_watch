# API Contract

> Status: outline only. Endpoints below are planned; the only implemented endpoint is
> `GET /health`. Contracts will be kept in sync with the FastAPI OpenAPI schema at `/docs`.

Base prefix: `/api/v1`

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness probe (`{"status": "ok"}`) — **implemented** |

## Chat (LLM layer)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/chat` | Grounded analyst chat. Body: `{"messages": [{"role": "user", "content": "..."}]}`. Response carries `reply`, `sources` (dataset provenance), `provider` (`openai-compatible` or `deterministic-fallback`), `guardrail_flags`, and `disclaimer`. **implemented** |

## Fires

| Method | Path | Description |
|---|---|---|
| GET | `/fires/hotspots` | Query active-fire observations (bbox, time range, source, confidence) |
| GET | `/fires/history` | Historical hotspot queries and counts |
| GET | `/fires/near` | Hotspots within buffer distance of a geometry or concession |

## Forecasting (Phase 2)

| Method | Path | Description |
|---|---|---|
| GET | `/forecasts` | Escalation probabilities by region/horizon (24h/48h/72h) |
| GET | `/forecasts/{run_id}` | Single forecast run with model version and calibration notes |

## Geospatial / concessions

| Method | Path | Description |
|---|---|---|
| GET | `/concessions` | List concession polygons (metadata + vintage; geometry may be aggregated publicly) |
| POST | `/concessions/intersect` | Geospatial intersection and buffering against observations |
| GET | `/concessions/{id}/exposure` | Hotspot counts, distance to fire, burned-area overlay |

## Synthetic companies

| Method | Path | Description |
|---|---|---|
| GET | `/companies` | List synthetic companies (all responses labeled synthetic) |
| GET | `/companies/{id}` | Company profile, assets, ownership |
| GET | `/companies/{id}/financials` | Multi-period synthetic statements |

## Credit

| Method | Path | Description |
|---|---|---|
| POST | `/credit/scenarios` | Run a stress scenario (land affected, disruption, revenue hit, costs, recovery) |
| GET | `/credit/scenarios/{run_id}` | Scenario result with calculation trace |
| GET | `/credit/monitoring` | Portfolio early-warning indicators |

## Insurance (Phase 4)

| Method | Path | Description |
|---|---|---|
| GET | `/insurance/accumulation` | TIV aggregation by region and hazard zone |
| POST | `/insurance/scenarios` | Hypothetical gross/net claims with deductibles and limits applied in documented order |

## Portfolio and provenance

| Method | Path | Description |
|---|---|---|
| GET | `/portfolio/concentration` | Exposure by sector and geography |
| GET | `/provenance/datasets` | Dataset provenance and licensing register |
| GET | `/provenance/models` | Model versions and evaluation metrics |

## Response conventions

- Every commercial/financial payload includes `"synthetic": true`.
- Scenario responses include `assumptions`, `calculation_trace`, `computed_at`.
- Observed events, forecasts and hypothetical losses are distinguished by an explicit
  `data_type` field (`observed` | `forecast` | `hypothetical`).
- Errors follow FastAPI's standard `{detail: ...}` shape; rate limits return 429.
