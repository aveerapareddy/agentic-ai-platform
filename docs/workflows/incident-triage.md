# Incident triage workflow

One-line purpose: describe **`incident_triage`** as implemented in the orchestrator—analyze → gather evidence → validate → governance on escalation—without duplicating [system-overview.md](../architecture/system-overview.md) or [data-flow.md](../architecture/data-flow.md).

## Scenario

An operator or integration starts an execution with `workflow_type: "incident_triage"` and structured input (at minimum an incident identifier such as `incident_id` or `id`, optionally `severity`). The platform plans three steps, runs them in order, enters validation phase semantics, then evaluates policy on a synthetic **`escalate_incident`** proposal. No external ticketing system is called; outcomes are **persisted** (execution graph, tool calls, policy rows, timeline).

## Step-by-step execution flow

| Order | Phase | What happens | Service(s) |
|------|--------|----------------|------------|
| 1 | Create | `ExecutionService.create_execution` writes **execution_context** and **execution** in `created`. | **orchestrator** (persistence via repository) |
| 2 | Plan | Status → `planning` → **Planner** emits revision v1: `analyze_incident` → `gather_evidence` → `validate_incident` with dependencies. Steps are materialized and saved. | **orchestrator** |
| 3 | Execute `analyze_incident` | Step runs. If **model-runtime** is configured (default), orchestrator calls `analyze_incident` with `IncidentAnalysisModelRequest`; on success, **step_result** holds `incident_summary`, `possible_causes`, and evidence pointing at model invocation. On failure, **StepExecutor** deterministic path; timeline records `model_reasoning` with `path: deterministic_fallback`. | **orchestrator**, **model-runtime** (or **StepExecutor** fallback) |
| 4 | Execute `gather_evidence` | Orchestrator calls **knowledge-service** `retrieve`, then **tool-runtime** for `incident_metadata_tool` and `signal_lookup_tool` (in that order). Each tool call is saved; timeline gets `knowledge_retrieved` and `tool_call_completed` per call. **step_result** merges retrieval chunks and tool outputs into `output` and `evidence`. | **orchestrator**, **knowledge-service**, **tool-runtime** |
| 5 | Execute `validate_incident` | Same pattern as analyze: **model-runtime** `validate_incident` when enabled, else **StepExecutor**. **step_result** includes `validation_outcome` when the model path is used. Execution moves to **`validating`** when non-validation steps have succeeded and the validation step is pending (orchestrator state rules). | **orchestrator**, **model-runtime** (or fallback) |
| 6 | Governance | After all steps **succeeded** while in **`validating`**, orchestrator creates **action_proposal** (`escalate_incident`), calls **policy-engine** `evaluate_proposal`, persists **policy_evaluation**, then branches allow / deny / conditional (see [policy-aware-execution.md](policy-aware-execution.md)). | **orchestrator**, **policy-engine** |

**Mukti** does not run on this hot path. Post-termination analysis is optional and separate ([mukti-agent.md](mukti-agent.md)).

## Where each capability is used

- **model-runtime**: `analyze_incident` and `validate_incident` only, when `ModelRuntimeService` is non-null and workflow is `incident_triage` (see `ExecutionEngine._should_use_model_for_step`).
- **tool-runtime**: `gather_evidence` only—`incident_metadata_tool`, `signal_lookup_tool`.
- **knowledge-service**: `gather_evidence` only—`KnowledgeService.retrieve` with tenant/workflow-scoped request.
- **policy-engine**: After validation success—evaluation of the `escalate_incident` proposal only (Phase 3 pack in `policy_engine.evaluator`).
- **Mukti**: Not invoked by `run_execution`. Use `build_mukti_analysis_input` + `MuktiService.analyze` + `FeedbackService.save_execution_feedback` after the run ends.

## Trace contents

`Execution.trace_timeline` is a list of objects shaped as `{ "event_type", "at", ... }`. Observed **event_type** values on this path include:

- `execution_status` — lifecycle (`planning`, `executing`, `validating`, `completed`, `failed`, `awaiting_approval`, …).
- `step_started`, `step_completed` — `step_id`, `planner_step_name`, `workflow_type`.
- `model_reasoning` — `path` (`model_runtime` | `deterministic_fallback`), `task`, optional `provider`, `error_class` / `error_message` on fallback.
- `knowledge_retrieved` — `retrieval_id`, `chunk_count`, `corpus_version`.
- `tool_call_completed` — `tool_call_id`, `tool_name`, `status`, `latency_ms`.
- `validation_performed` — on validation step completion; includes `validation_status` from step output when present.
- `action_proposed`, `policy_evaluated`, `governed_outcome`, and for conditional policy: `approval_required`, `approval_received`.

Normalized rows (via repository): **execution_plans**, **execution_steps**, **step_results**, **tool_calls**, **action_proposals**, **policy_evaluations**, **approvals** (when applicable).

## Final result shape

On **allow** (default `dev` + `policy_scope` not `phase3_deny` / not triggering conditional): `execution.status` is **`completed`**, `result` includes triage fields (`incident_summary`, `likely_cause`, `evidence_summary`, `validation_status`, `confidence_score`, …), plus `proposed_action`, `policy_decision: "allow"`, `approval_status: "not_required"`.

On **deny**: `failed`, `outcome: "failed"`, `policy_decision: "deny"`, timeline includes `governed_outcome` with `path: policy_denied`.

On **conditional**: `awaiting_approval` until `ExecutionService.submit_approval`; then `completed` or `failed` depending on approve/reject.

## Intentional simplifications

- **api-gateway** is not implemented; callers use `ExecutionService` or tests.
- Escalation is a **recorded proposal** and policy outcome, not a live ticket mutation.
- **feedback-service** is not called from `ExecutionEngine`; operator feedback is wired in tests and would follow API design when gateway exists.
