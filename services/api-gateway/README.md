# API Gateway (Phase 8)

Thin **HTTP ingress** for the platform: validates requests, enforces **RBAC** and **tenant scope**, maps JSON to orchestrator and feedback-service calls, exposes **policy inspection/simulation** via policy-engine, and returns projections aligned with [docs/architecture/api-design.md](../../docs/architecture/api-design.md). **No workflow or tool logic** lives here; **policy decisions** are evaluated only in **policy-engine**.

## Python package layout

Runnable code lives under **`gateway/`** (not `app/`) because the orchestrator already owns the top-level `app` package. A stub `app/README.md` notes this for readers expecting `services/api-gateway/app/`.

## Operational routes (not `/v1`)

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/metrics` | Prometheus text from in-memory operational registry (`platform-observability`). |
| `GET` | `/health/runtime` | Lightweight runtime health including configured `model_provider`. |

Business evaluation aggregates remain under **`GET /v1/metrics`**.

## Implemented `/v1` routes

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/v1/executions` | Creates execution via `ExecutionService`; optional background `start_execution` (`GATEWAY_SCHEDULE_EXECUTION_START`, default true). |
| `GET` | `/v1/executions/{execution_id}` | Reads execution from repository. |
| `GET` | `/v1/executions` | Lists executions (`tenant_id`, `workflow_type`, `status`, `limit` query params). |
| `GET` | `/v1/executions/{execution_id}/trace` | Materialized trace from stored steps, results, tool calls, policy evaluations, approvals, timeline. |
| `POST` | `/v1/executions/{execution_id}/approvals` | Delegates to `ExecutionEngine.submit_approval` (orchestrator). |
| `POST` | `/v1/executions/{execution_id}/feedback` | Delegates to `FeedbackService.submit_operator_feedback`. |
| `POST` | `/v1/executions/{execution_id}/replay` | Delegates to orchestrator `ReplayService`: child execution, `parent_execution_id`, provenance under `__replay_provenance__`, `replay_created` trace event; optional `start_execution`. |
| `POST` | `/v1/executions/{execution_id}/cancel` | Requests cancellation; orchestrator transitions to `cancelled` when allowed. |

Background runs (`execution_mode: background` + `GATEWAY_USE_EXECUTION_WORKER_QUEUE=true`) enqueue work for the in-process worker instead of blocking the HTTP handler.
| `GET` | `/v1/executions/{execution_id}/replay-diff/{replay_execution_id}` | Delegates to `ReplayDiffService`: structured `ReplayDiffSummary` (read-only comparison of stored artifacts). |
| `GET` | `/v1/policies` | Lists deterministic rule descriptors from policy-engine (**admin** role). |
| `POST` | `/v1/policies/simulate` | What-if policy evaluation (**admin** role); does not mutate rules. |

## Auth (Session E — local/dev)

Headers: `X-Principal-Id`, `X-Tenant-Id`, `X-Roles` (comma-separated: `viewer`, `operator`, `approver`, `admin`).

Environment:

| Variable | Default | Meaning |
|----------|---------|---------|
| `GATEWAY_ALLOW_DEV_PRINCIPAL_FALLBACK` | `true` | Use dev principal when headers omitted |
| `GATEWAY_DEV_PRINCIPAL_ID` | `dev-operator` | Fallback principal |
| `GATEWAY_DEV_TENANT_ID` | `dev-tenant` | Fallback tenant |
| `GATEWAY_DEV_ROLES` | `operator,admin` | Fallback roles |

Execution create merges trusted tenant/principal into `context`; conflicting `context.tenant_id` returns **400**.

## Supported `workflow_type` values (gateway allowlist)

- `incident_triage`
- `cost_attribution`
- `generic`

(Others return `400` until registered here and implemented in the orchestrator.)

## Run (development)

Install **`common-schemas`** editable first (orchestrator depends on it by name), then **only** the gateway editable. Pip resolves `orchestrator-service @ file:../orchestrator` from the gateway metadata and pulls `feedback-service` and the rest—**do not** also pass `-e ../orchestrator` or `-e ../feedback-service` on the same line, or pip often raises `ResolutionImpossible` (same version, two different “direct” requirements).

```bash
cd services/api-gateway
pip install -e ../../packages/common-schemas -e .
uvicorn gateway.main:app --host 127.0.0.1 --port 8080
```

If you already use a venv where `orchestrator-service` is installed editable on its own, reinstall with the command above or upgrade with `pip install -e .` from this directory so the resolver sees a single graph.

Tests:

```bash
cd services/api-gateway
python -m pytest gateway/tests -q
```

## Intentionally not built (Phase 8 scope)

- Operator console UI
- Full authentication / authorization (placeholder hook only)
- Metrics / evaluation-engine routes
- Durable idempotency store (in-memory per process only)
- Dedicated replay metadata table (provenance currently in `execution.input`); replay diff UI
- Separate HTTP orchestrator process (in-process wiring only)

## Orchestrator additions

`Repository` includes `list_executions`, `list_executions_by_parent`, and `list_approvals_for_execution`. Replay construction is owned by `app.services.replay_service.ReplayService`; comparison by `app.services.replay_diff_service.ReplayDiffService` (not the gateway).
