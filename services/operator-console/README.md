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

## Components

- **execution-list** — table of list items; row opens detail.
- **execution-summary** — workflow, status, timestamps, result/governance/validation snippets (read-only projections).
- **execution-metrics** — per-execution metrics section (server-computed only).
- **execution-replay-panel** — request exact or investigative replay (`POST …/replay`); shows lineage when viewing a replay child; links to replay detail and diff after create.
- **trace-timeline** — timeline events, steps, tool calls, policy evaluations, approvals.
- **approval-panel** — approve/reject through gateway.

## API layer

- **execution-api.service** — executions, trace, approvals.
- **metrics-api.service** — execution and platform metrics.
- **insights-api.service** — Mukti v2 insights.
- **replay-api.service** — `POST /v1/executions/{id}/replay`, `GET /v1/executions/{source}/replay-diff/{replay}` (no client-side replay or diff logic).

## Replay UX

- **Exact replay:** same business input; no overrides required.
- **Investigative replay:** requires **reason** or **label**; optional JSON object for `input_overrides` (validated in UI before submit).
- After create: links to open the replay execution or the replay diff page (no auto-navigation).
- Diff page: summary cards, items grouped by category; severity colors per ui-system (info / warning / significant); values expand on demand.

## Limitations

- No replay diff computation in the browser.
- No advanced trace graph or side-by-side timeline visualization (Session 4+).
- Listing bounded by gateway `limit`; no server-side `execution_id` search filter.

## Run

1. Start **api-gateway** (e.g. port `8080`).  
2. Dev server proxies `/v1` → gateway ([`proxy.conf.json`](./proxy.conf.json)).

```bash
cd services/operator-console
npm install
npm start
```

Open `http://127.0.0.1:4200`. For production builds, set `API_BASE_URL` via `API_BASE_URL` token provider.

## Tests

```bash
npm test
```

Light coverage: replay API, replay panel validation, replay diff grouping, routes, execution detail wiring.

## Intentionally not in this phase

- Advanced trace visualization / graph compare (Session 4).
- Mukti insight detail drill-down; evaluation anomalies page.
- Policy administration, feedback submission UI, full enterprise auth.
- Charts or client-side metric/diff computation.
