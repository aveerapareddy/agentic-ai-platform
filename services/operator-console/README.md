# Operator Console (Phase 8)

Minimal **internal** Angular UI over **api-gateway** only ([system-overview.md](../../docs/architecture/system-overview.md) trust boundary). No direct calls to orchestrator, policy-engine, or tool-runtime from the browser.

## Pages

| Route | Purpose |
|-------|---------|
| `/executions` | List executions (`GET /v1/executions`), filters for `tenant_id`, `workflow_type`, `status`, client-side substring search on `execution_id`. |
| `/executions/:executionId` | Detail (`GET /v1/executions/{id}`), trace (`GET /v1/executions/{id}/trace`), **evaluation metrics** (`GET /v1/executions/{id}/metrics`), approval panel when `status === awaiting_approval` (`POST …/approvals`). |
| `/metrics` | Platform aggregates (`GET /v1/metrics`) — workflow, step-type, tool, and policy rollups from evaluation-engine via gateway. |
| `/insights` | Mukti v2 cross-execution insights (`GET /v1/insights/mukti`) — advisory failure patterns, policy friction, ranked suggestions. |

## Components

- **execution-list** — table of list items; row opens detail.
- **execution-summary** — workflow, status, timestamps, result/governance/validation snippets (read-only projections).
- **execution-metrics** — per-execution metrics section (server-computed only; loading / empty / error states).
- **trace-timeline** — timeline events, steps, tool calls, policy evaluations, approvals (from trace payload).
- **approval-panel** — approve/reject through gateway; reloads detail after success.

## API layer

- **execution-api.service** — executions, trace, approvals.
- **metrics-api.service** — `GET /v1/executions/{id}/metrics`, `GET /v1/metrics` (thin HTTP only; no client-side metric computation).
- **insights-api.service** — `GET /v1/insights/mukti` (thin HTTP only; no client-side insight computation).

## Run

1. Start **api-gateway** (e.g. port `8080`).  
2. Dev server proxies `/v1` → gateway ([`proxy.conf.json`](./proxy.conf.json)).

```bash
cd services/operator-console
npm install
npm start
```

Open `http://127.0.0.1:4200`. For production builds, set `API_BASE_URL` via a custom provider for `API_BASE_URL` token (see `src/app/core/api/api-base-url.token.ts`) so requests target the real gateway origin.

## Tests

```bash
npm test
```

Uses Karma with `builderMode: "application"` in `angular.json`. Light coverage: metrics API shape, metrics page, execution detail metrics wiring, execution-metrics component, routes.

## Intentionally not in this phase

- Mukti insight detail drill-down UI (`GET /v1/insights/mukti/{id}` available via API; list page only for now).
- Evaluation-engine anomaly page (`GET /v1/insights/anomalies` separate from Mukti v2).
- Policy administration UI.
- Charts, KPI widgets, or client-side metric recomputation.
- Full enterprise auth (gateway placeholder only).
- Feedback submission UI (gateway supports `POST …/feedback`; can be added later).
- Replay UI.
- Rich design system / marketing visuals.

## Gap note

Listing is bounded by gateway `limit` (UI requests up to 200). There is **no** server-side `execution_id` filter; deep search across all runs would need a gateway/API extension.
