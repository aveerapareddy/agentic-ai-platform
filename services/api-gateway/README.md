# API Gateway (Phase 8)

Thin **HTTP ingress** for the platform: validates requests, maps JSON to orchestrator and feedback-service calls, returns projections aligned with [docs/architecture/api-design.md](../../docs/architecture/api-design.md). **No workflow, policy, or tool logic** lives here.

## Python package layout

Runnable code lives under **`gateway/`** (not `app/`) because the orchestrator already owns the top-level `app` package. A stub `app/README.md` notes this for readers expecting `services/api-gateway/app/`.

## Implemented `/v1` routes

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/v1/executions` | Creates execution via `ExecutionService`; optional background `start_execution` (`GATEWAY_SCHEDULE_EXECUTION_START`, default true). |
| `GET` | `/v1/executions/{execution_id}` | Reads execution from repository. |
| `GET` | `/v1/executions` | Lists executions (`tenant_id`, `workflow_type`, `status`, `limit` query params). |
| `GET` | `/v1/executions/{execution_id}/trace` | Materialized trace from stored steps, results, tool calls, policy evaluations, approvals, timeline. |
| `POST` | `/v1/executions/{execution_id}/approvals` | Delegates to `ExecutionEngine.submit_approval` (orchestrator). |
| `POST` | `/v1/executions/{execution_id}/feedback` | Delegates to `FeedbackService.submit_operator_feedback`. |
| `POST` | `/v1/executions/{execution_id}/replay` | **Stub**: creates a new `CREATED` execution with `parent_execution_id`, copies input + `_gateway_replay_stub` metadata; does **not** auto-run or enforce replay policy (future work). |

## Supported `workflow_type` values (gateway allowlist)

- `incident_triage`
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
- Production replay policy, sandbox routing, and child-run execution semantics beyond the stub above
- Separate HTTP orchestrator process (in-process wiring only)

## Orchestrator additions

`Repository` now includes `list_executions` and `list_approvals_for_execution` so the gateway can list and build trace projections without bypassing the persistence port. `ExecutionService.create_execution` accepts optional `parent_execution_id` and passes `feature_flags` through for replay stub context.
