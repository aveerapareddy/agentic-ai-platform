# Data flow

One-line purpose: end-to-end data flow for **`incident_triage`** as implemented—complementing [system-overview.md](system-overview.md) interaction tables.

## 1. Execution creation

Caller (today: `ExecutionService` / tests / `app.main`) supplies `workflow_type`, structured `input`, and tenant/environment/policy fields. **execution_context** row is written, then **executions** row in `CREATED`. No Mukti involvement.

## 2. Planning

Orchestrator transitions to **PLANNING**; **Planner** builds **execution_plans** revision v1 (analyze → gather → validate with dependencies). **execution_steps** rows are materialized from plan specs; each step’s `input` includes `planner_step_name`, `workflow_type`, and `execution_input` snapshot.

## 3. Reasoning (`analyze_incident`)

Step moves **PENDING → RUNNING**. If **model-runtime** is enabled (default):

- Orchestrator builds `IncidentAnalysisModelRequest` from execution context facts (bounded excerpt of `execution.input`).
- **model-runtime** returns `IncidentAnalysisReasoningOutput`; orchestrator maps to **step_results** (`incident_summary`, `possible_causes`) and appends `model_reasoning` (`path: model_runtime`) to **trace_timeline**.

On failure or disabled model-runtime: **StepExecutor** produces deterministic output; timeline records `deterministic_fallback`.

## 4. Evidence gathering (`gather_evidence`)

Orchestrator calls **knowledge-service** `retrieve` → timeline `knowledge_retrieved`. Then **tool-runtime** invokes `incident_metadata_tool` and `signal_lookup_tool` → each persisted as **tool_calls** row; timeline `tool_call_completed`. **step_results** hold merged output and **evidence** entries (retrieval chunks + tool references).

## 5. Validation (`validate_incident`)

Same model-runtime vs fallback pattern as analyze; **ValidationOutcome** on **step_results** when model path used. Orchestrator enters **VALIDATING** when non-validation steps have completed and validation step is pending (per existing state rules).

## 6. Governance (post-validation success set)

For `incident_triage`, after all steps **SUCCEEDED** in **VALIDATING**, orchestrator creates **action_proposal** (`escalate_incident`), persists it, calls **policy-engine**, persists **policy_evaluation**, branches:

- **allow** → proposal approved, execution **COMPLETED**, result payload includes governance summary.
- **conditional** → **AWAITING_APPROVAL**; later **submit_approval** resumes.
- **deny** → **FAILED**; trace includes `governed_outcome` with `path: policy_denied`.

No external ticket system is called; effects are **recorded** only.

## 7. Post-execution feedback and Mukti

**Not** on the completion critical path. A separate sequence:

1. Optional **feedback-service** `submit_operator_feedback` → **operator_feedback** rows.
2. **build_mukti_analysis_input** reads **execution**, **steps**, **step_results**, **list_policy_evaluations_for_execution**, **list_action_proposals_for_execution**, plus operator feedback list.
3. **MuktiService.analyze** → `ExecutionFeedback` (failure_types, patterns_detected, improvement_suggestions, advisory_confidence).
4. **feedback-service** `save_execution_feedback` → **execution_feedback** row.

Execution row is **not** updated by Mukti.

## Data residency and classification

Logical separation: execution OLTP in PostgreSQL (or in-memory test store); knowledge corpus in knowledge-service process; no cross-border guarantees in code—**deployment** defines residency and classification policies.
