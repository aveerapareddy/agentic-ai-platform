# Observability and reliability

One-line purpose: how operators observe executions, classify failures, and reason about replay and fallbacks—grounded in current implementation.

## Execution trace

- **Timeline:** `executions.trace_timeline` holds ordered events (`step_started`, `step_completed`, `knowledge_retrieved`, `tool_call_completed`, `model_reasoning`, `policy_evaluated`, `governed_outcome`, `validation_performed`, `execution_status`, etc.).
- **Normalized rows:** `execution_steps`, `step_results`, `tool_calls`, `policy_evaluations`, `approvals`, `action_proposals` enable queryable detail and joins for replay narratives (per `001_initial_schema.sql` header comments).

**No separate `traces` table** by design; materialization is reconstructive from stored rows + timeline.

## State transitions

Execution and step transitions are **validated** in code (`state_machine.py`); invalid transitions raise. Terminal states are **completed**, **failed**, **cancelled**; **awaiting_approval** pauses progress until approval API path runs.

## Failure classes

Aligned with **runtime-model.md** §7: tool, planning, validation, policy, timeout (timeout paths may be partial in current code—escalate explicitly if adding production SLAs). Failures are **recorded** on steps, tool calls, or execution result—not silently swallowed.

## Fallback behavior

- **Model-runtime:** on exception or disabled service, orchestrator uses **deterministic StepExecutor** for the same step and emits `model_reasoning` with `path: deterministic_fallback`. Completion does **not** depend on a live LLM.
- **Knowledge / tools:** failures surface as step/tool errors per workflow rules; no hidden degradation to success.

## Replayability

Stored **inputs**, **plan** revisions, **step** graph, **tool_call** inputs/outputs, and **policy evaluation** inputs support structural replay per runtime model §9. **Exact stochastic replay** of model output is not guaranteed unless inference is pinned—out of scope for the fake provider.

## Logging, metrics, distributed tracing

**Operational layer (`packages/observability`):**

- Structured JSON events to stdout (`model_request`, `model_retry`, `tool_invoke`, `replay_created`, `model_fallback`, etc.) with `execution_id` / `step_id` — **no raw prompts**.
- In-memory counters and latency totals; Prometheus text via **`GET /metrics`** on api-gateway (not `/v1/metrics`, which serves evaluation aggregates).
- **Policy-engine counters** (incremented on `evaluate_proposal` and `simulate_policy`, not in evaluation aggregates): `policy_evaluations_total`, `policy_decision_allow_total`, `policy_decision_deny_total`, `policy_decision_conditional_total`, `policy_simulations_total`.
- OpenTelemetry-lite span helpers (`observability.span`) without an OTel SDK dependency.

**Model-runtime** records token usage and latency on `ModelInvocationTelemetry` (trace `model_reasoning.invocation` and structured output metadata). Retries are bounded and classified (transient vs schema validation).

**Business / evaluation metrics** remain in `evaluation-engine` and `GET /v1/metrics` — trace-grounded, not operational counters.

Distributed backends (Datadog, Grafana Cloud, etc.) are deployment choices; this repo does not ship dashboards or SLO gates.

## Execution streaming (Session F)

- **Transport:** `GET /v1/executions/{execution_id}/stream` — **Server-Sent Events** (`text/event-stream`).
- **Source of truth:** api-gateway **polls** the orchestrator repository snapshot (status, steps, timeline, approvals); no UI-side state machine and no distributed event bus.
- **Event types:** `execution_updated`, `step_updated`, `trace_event`, `approval_required`, `execution_completed`, `execution_failed`, `execution_cancelled`, `replay_created`, `heartbeat` (see `common_schemas.streaming`).
- **Observability:** `execution_stream_opened`, `execution_stream_closed`, `execution_stream_events_total`, `execution_stream_errors_total`, `execution_streams_active` / `execution_streams_closed_total` via `platform-observability`.
- **Limits:** Poll interval default 500ms; max stream duration 600s; payloads bounded (no raw prompts or stack traces). Operator-console uses **fetch + SSE parse** so dev auth headers apply (browser `EventSource` cannot set custom headers).

## Runbooks and on-call

`docs/runbooks/` exists; **local-development** and similar files may remain light until operations harden. Production on-call playbooks are a **non-goal** for the current portfolio phase (per end-state).

## Reliability expectations

Single-process tests demonstrate **logical** reliability (state machine, persistence round-trips). **HA, multi-AZ, and chaos** are not validated here.
