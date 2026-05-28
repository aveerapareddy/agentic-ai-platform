# Operator Console (Phase 8)

Minimal **internal** Angular UI over **api-gateway** only ([system-overview.md](../../docs/architecture/system-overview.md) trust boundary). No direct calls to orchestrator, policy-engine, or tool-runtime from the browser.

## Pages

| Route | Purpose |
|-------|---------|
| `/executions` | List executions (`GET /v1/executions`), filters for `tenant_id`, `workflow_type`, `status`, client-side substring search on `execution_id`. |
| `/executions/:executionId` | Detail (`GET /v1/executions/{id}`), trace (`GET /v1/executions/{id}/trace`), evaluation metrics, **replay request** panel, approvals when gated. |
| `/executions/:sourceId/replay-diff/:replayId` | **Replay diff** (`GET /v1/executions/{source}/replay-diff/{replay}`) — server-computed comparison grouped by category and severity. |
| `/metrics` | Platform aggregates (`GET /v1/metrics`). |
| `/insights` | Mukti v2 cross-execution insights (`GET /v1/insights/mukti`). |
| `/policies` | Policy rule catalog and simulation (`GET /v1/policies`, `POST /v1/policies/simulate`). Read-only; no rule editing. |

Execution detail subscribes to **`GET /v1/executions/{id}/stream`** (SSE) for live status, trace append, step updates, and approval visibility. Uses `ExecutionStreamService` (fetch + SSE parse with auth headers). Stops on terminal states; no client-side orchestration.

## Components

- **execution-list** — table of list items; row opens detail.
- **execution-summary** — workflow, status, timestamps, result/governance/validation snippets (read-only projections).
- **execution-metrics** — per-execution metrics section (server-computed only).
- **execution-replay-panel** — request exact or investigative replay (`POST …/replay`); shows lineage when viewing a replay child; links to replay detail and diff after create.
- **trace-timeline** — grouped trace timeline (execution + step sections, model/tool/policy/error buckets), event cards with expandable payload fields, related tool/policy/approval records.
- **approval-panel** — approve/reject through gateway.

## API layer

- **execution-api.service** — executions, trace, approvals.
- **metrics-api.service** — execution and platform metrics.
- **insights-api.service** — Mukti v2 insights.
- **replay-api.service** — `POST /v1/executions/{id}/replay`, `GET /v1/executions/{source}/replay-diff/{replay}` (no client-side replay or diff logic).
- **policy-api.service** — policy list and simulation (admin role required at gateway).

## Auth headers (local dev)

`authHeadersInterceptor` attaches `X-Principal-Id`, `X-Tenant-Id`, and `X-Roles` from `dev-auth-headers.ts` for local gateway use. Production deployments should rely on the gateway edge to inject identity; the UI must not become the source of truth for policy rules.

## Replay UX

- **Exact replay:** same business input; no overrides required.
- **Investigative replay:** requires **reason** or **label**; optional JSON object for `input_overrides` (validated in UI before submit).
- After create: links to open the replay execution or the replay diff page (no auto-navigation).
- Diff page: summary cards, items grouped by category; severity colors per ui-system (info / warning / significant); values expand on demand.

## Trace timeline (Session 4)

- Events from `GET /v1/executions/{id}/trace` only; grouped and sorted in the UI for readability (no semantic inference).
- **Step groups** show status, type, step duration (when `step_result.latency_ms` exists), and counts of model/tool/policy/error events.
- **Sections** within each step: execution & steps, model runtime, tools & retrieval, policy & approval, errors & failures.
- Per-event: type label, timestamp, summary, optional `latency_ms` from the event row, collapsed field list + optional raw JSON.
- **Total execution latency** shown when evaluation metrics (`total_latency_ms`) are loaded — not invented from timeline alone.
- **Model path** badge (`model_runtime` / `deterministic_fallback`) from last `model_reasoning` row for the step (display only).

## Limitations

- No replay diff computation in the browser.
- No trace graph / DAG / side-by-side timeline compare (future work).
- Listing bounded by gateway `limit`; no server-side `execution_id` search filter.
- Trace grouping uses fields present on gateway rows; missing latency or step metadata is omitted rather than estimated.

## Run

### Docker (with api-gateway)

From repo root: `make docker-up` → open **http://localhost:4200**. nginx serves the built app and proxies `/v1`, `/metrics`, and `/health/` to the `api-gateway` service ([`docker/nginx-console.conf`](../../docker/nginx-console.conf)).

### Host dev server

1. Start **api-gateway** (e.g. port `8080`).  
2. Dev server proxies `/v1` → gateway ([`proxy.conf.json`](./proxy.conf.json)).

```bash
make run-console
# or: cd services/operator-console && npm install && npm start
```

Open `http://127.0.0.1:4200`. For custom API hosts, set `API_BASE_URL` via the token provider.

### Health

- Static UI: nginx `GET /` (compose healthcheck).
- API/runtime: proxied `GET /health/runtime` on the gateway.

## Tests

```bash
npm test
```

Light coverage: replay API, replay panel validation, replay diff grouping, trace grouping util, trace timeline component, routes, execution detail wiring.

## Intentionally not in this phase

- Trace graph / DAG visualization and cross-execution trace compare.
- Mukti insight detail drill-down; evaluation anomalies page.
- Policy administration, feedback submission UI, full enterprise auth.
- Charts or client-side metric/diff computation.
