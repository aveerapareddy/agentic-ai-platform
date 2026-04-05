# Use cases

One-line purpose: map high-signal workflows to platform capabilities—with honest coverage of what is implemented.

## Incident triage and root cause analysis

**Problem:** Incidents require structured triage, correlated evidence, validation, and sometimes escalation—without uncontrolled mutations or unauditable model-only decisions.

**Workflow summary (implemented):**

1. Create execution (`incident_triage`) with structured input (e.g. `incident_id`).
2. Planner emits `analyze_incident` → `gather_evidence` → `validate_incident`.
3. **Analyze / validate**: `model-runtime` (default fake structured provider) with **deterministic fallback** to `StepExecutor` if model-runtime is disabled or errors; trace records `model_reasoning` path.
4. **Gather evidence**: orchestrator calls **knowledge-service** retrieval and **tool-runtime** (`incident_metadata_tool`, `signal_lookup_tool`); persists **tool_calls**; attaches **evidence** to the step result.
5. After non-validation steps succeed, execution enters **validating**; validation step runs, then governance finalizes **escalate_incident** proposal via **policy-engine** (allow / conditional / deny) and **approvals** when required.

**Capabilities exercised:** execution lifecycle, planner, model-runtime boundary, tool-runtime, knowledge-service, validation gate, policy, proposals, approvals, trace timeline + normalized persistence.

## Cross-system cost attribution and optimization

**Problem:** Cost and usage questions span billing APIs, resource metadata, and organizational context; answers should be evidence-backed and access-controlled.

**Workflow summary (intended):** Retrieval and read-only tools over cost APIs, validation of attributed numbers, policy on any state-changing recommendations—mirroring the incident pattern with cost-specific steps.

**Platform capabilities exercised today:** Only the **generic** planner path (reasoning → validation) and **StepExecutor** simulation. **Not implemented:** cost-specific tools, corpora, or validators. This use case remains **design-aligned** but **not productized** in code.

## Policy-aware action execution

**Problem:** High-impact actions must be **evaluated**, sometimes **denied** or **approval-gated**, and always **auditable**.

**Workflow summary (implemented on incident triage completion):** Action proposal for `escalate_incident`; synchronous policy evaluation; branches to completed (allow), `awaiting_approval` (conditional), or failed (deny); approvals persisted and traced.

**Capabilities exercised:** policy-engine, action proposals, policy_evaluations, approvals, trace events (`policy_evaluated`, `governed_outcome`, etc.), constitution §3 separation.

## Mukti Agent (post-execution analysis and improvement)

**Problem:** After completion, teams need **structured** signals—failure classes, patterns, suggestions—for runbooks and change processes, without altering live executions.

**Workflow summary (implemented):** Build `MuktiAnalysisInput` from stored execution, steps, results, operator feedback list, policy evaluations, and proposals (`build_mukti_analysis_input`). **MuktiService** runs a **deterministic rule pack**; output is **ExecutionFeedback** persisted via **feedback-service**. Execution rows are **unchanged**.

**Capabilities exercised:** operator_feedback vs execution_feedback separation, advisory-only output, trace-driven classification (e.g. `trace_policy_denied`, `model_deterministic_fallback`, `clean_success_path`).

## Cross-cutting requirements

Each use case above (where implemented) relies on: **shared schemas**, **relational persistence** for the execution graph and governance artifacts, **full traceability** per constitution §4.1, and **no Mukti → orchestrator control** channel.
