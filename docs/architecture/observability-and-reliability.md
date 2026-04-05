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

**Not implemented** as standardized pipelines in this repository: no mandatory OpenTelemetry wiring, no SLO dashboards checked in. Operators should attach platform logging/metrics at deployment. Semantics for what to log are implied by trace events and repository writes.

## Runbooks and on-call

`docs/runbooks/` exists; **local-development** and similar files may remain light until operations harden. Production on-call playbooks are a **non-goal** for the current portfolio phase (per end-state).

## Reliability expectations

Single-process tests demonstrate **logical** reliability (state machine, persistence round-trips). **HA, multi-AZ, and chaos** are not validated here.
