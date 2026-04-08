# Operator Console (Phase 8)

Minimal **internal** Angular UI over **api-gateway** only ([system-overview.md](../../docs/architecture/system-overview.md) trust boundary). No direct calls to orchestrator, policy-engine, or tool-runtime from the browser.

## Pages

| Route | Purpose |
|-------|---------|
| `/executions` | List executions (`GET /v1/executions`), filters for `tenant_id`, `workflow_type`, `status`, client-side substring search on `execution_id`. |
| `/executions/:executionId` | Detail (`GET /v1/executions/{id}`), trace (`GET /v1/executions/{id}/trace`), approval panel when `status === awaiting_approval` (`POST …/approvals`). |

## Components

- **execution-list** — table of list items; row opens detail.
- **execution-summary** — workflow, status, timestamps, result/governance/validation snippets (read-only projections).
- **trace-timeline** — timeline events, steps, tool calls, policy evaluations, approvals (from trace payload).
- **approval-panel** — approve/reject through gateway; reloads detail after success.

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

Uses Karma with `builderMode: "application"` in `angular.json` so specs are discovered for the `application` build target (default `browser` mode runs **0** tests). Light coverage: HTTP service shape, routes, approval panel behavior.

## Intentionally not in this phase

- Metrics dashboards, Mukti insights UI, policy administration UI ([project-end-state.md](../../docs/overview/project-end-state.md) Phase 8 stubs).
- Full enterprise auth (gateway placeholder only).
- Feedback submission UI (gateway supports `POST …/feedback`; can be added later).
- Replay UI.
- Rich design system / marketing visuals.

## Gap note

Listing is bounded by gateway `limit` (UI requests up to 200). There is **no** server-side `execution_id` filter; deep search across all runs would need a gateway/API extension.
