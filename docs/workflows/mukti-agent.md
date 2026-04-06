# Mukti agent workflow

One-line purpose: **post-execution** analysis that reads frozen execution artifacts and optional operator feedback, then persists **execution_feedback**—aligned with constitution §6.2–6.3 and `mukti_agent.analyzer.MuktiAnalyzer`.

## Scenario description

An execution has reached a **terminal** (or for analysis purposes, stable) state. An operator or batch job has optionally submitted **operator feedback** via **feedback-service**. A caller builds **`MuktiAnalysisInput`** from the execution repository and passes it to **`MuktiService.analyze`**. The analyzer emits **`ExecutionFeedback`**, which is stored via **`FeedbackService.save_execution_feedback`**. The live **execution** row is unchanged.

## Where model-runtime, tool-runtime, knowledge-service, policy-engine, and Mukti run

| Capability | Used? | Notes |
|------------|-------|--------|
| **model-runtime** | No | Mukti uses rule-based `MuktiAnalyzer` in this repo. |
| **tool-runtime** | No | Analysis reads persisted rows only. |
| **knowledge-service** | No | Not invoked during Mukti. |
| **policy-engine** | No | Prior **policy_evaluation** rows are **inputs** to Mukti, not re-evaluated. |
| **Mukti** (`mukti-agent`) | Yes | `MuktiService` / `MuktiAnalyzer` produce `ExecutionFeedback`. |

**feedback-service** stores operator feedback and the Mukti output; it does not run the analyzer itself (callers orchestrate: build input → analyze → save).

## Step-by-step execution flow

| Step | Service / component | Action |
|------|---------------------|--------|
| 1 | Caller (test, script, future gateway) | `submit_operator_feedback` on **feedback-service** if labels/context are needed. |
| 2 | Caller + **orchestrator** repository | `build_mukti_analysis_input(repo, execution_id, operator_feedback=...)` loads execution, steps, step results, policy evaluations, action proposals. |
| 3 | **mukti-agent** | `MuktiService().analyze(inp)` → `ExecutionFeedback`. |
| 4 | **feedback-service** | `save_execution_feedback(record)`; list with `list_execution_feedback_for_execution`. |

## Inputs (build_mukti_analysis_input)

Fields populated by **`build_mukti_analysis_input`** (`services/orchestrator/app/support/mukti_input.py`):

- **execution** — includes **`trace_timeline`** (read for patterns such as `governed_outcome` / `model_reasoning`).
- **step_records** — each **Step** with optional **StepResult** from `get_step_result`.
- **policy_evaluations** — `list_policy_evaluations_for_execution`.
- **action_proposals** — `list_action_proposals_for_execution`.
- **operator_feedback** — from **feedback-service** `list_operator_feedback_for_execution` when supplied.

`MuktiAnalysisInput` is defined in `common_schemas.mukti_input`.

## Analysis pipeline (implemented)

`MuktiService` delegates to **`MuktiAnalyzer.analyze`** (deterministic rule pack `deterministic_rule_pack_v1`):

1. Inspect **terminal status** (`failed`, `cancelled`) → `failure_types`.
2. Any step **failed** → `step_failure` in `failure_types`.
3. Any **policy_evaluation** with decision **deny** → `policy_evaluation_deny` + optional `ImprovementSuggestion` (category `policy_rule`).
4. Scan **trace_timeline** for `governed_outcome` / `policy_denied` and for `model_reasoning` with `path: deterministic_fallback` → patterns such as `model_deterministic_fallback`.
5. **action_proposal** in `policy_denied` status → further failure typing and suggestions.
6. **Operator feedback** with label **`false_positive`** (case-insensitive) → pattern `operator_disputed_outcome`.
7. If execution **completed** and no failure types accumulated → pattern **`clean_success_path`**.

Output is **`ExecutionFeedback`** (`feedback_id`, `failure_types`, `patterns_detected`, `improvement_suggestions`, `advisory_confidence`, …).

## What the trace contains (for Mukti)

Mukti **reads** the execution’s **`trace_timeline`** and normalized artifacts in **`MuktiAnalysisInput`**; it does **not** append to `trace_timeline`. Pattern detection uses timeline entries (e.g. `model_reasoning` with `deterministic_fallback`, `governed_outcome` with `policy_denied`) plus policy and proposal rows.

## Final result shape (`ExecutionFeedback`)

Persisted advisory record (see `common_schemas.feedback.ExecutionFeedback`):

- **`feedback_id`**, **`execution_id`**, optional **`source_scope`** (e.g. `{"analyzer": "deterministic_rule_pack_v1"}`).
- **`failure_types`**: deduplicated strings (`terminal_failed`, `policy_evaluation_deny`, `trace_policy_denied`, …) when rules match.
- **`patterns_detected`**: `PatternDetection` list (`pattern_type`, `description`, `evidence`)—e.g. `clean_success_path`, `model_deterministic_fallback`, `operator_disputed_outcome`.
- **`improvement_suggestions`**: `ImprovementSuggestion` list (`category`, `summary`, `detail`) for policy-related hints when applicable.
- **`advisory_confidence`**: scalar set by the analyzer (e.g. `0.84`); not a validation verdict.

## Outputs

- Callers persist via **feedback-service** `save_execution_feedback` (in-memory repository by default in tests).
- Read back with `list_execution_feedback_for_execution`.

## Control boundaries

- **Mukti** must not call `ExecutionEngine.run_execution` or `submit_approval`.
- **feedback-service** does not drive execution lifecycle; it only stores operator feedback and Mukti rows.
- In this repository, **orchestrator** does not automatically invoke feedback-service after completion; integration is explicit (tests, future gateway).

## Relationship to observability

Timeline and normalized rows remain the **system-of-record** narrative for a run. Mukti adds a **derived** document for review and improvement processes—not a replacement for trace storage.

## What Mukti does not do

- Mutate live executions or replay runs automatically.
- Replace policy-engine or tool-runtime decisions.
- Run inside the hot path of `gather_evidence` or governance (see [data-flow.md](../architecture/data-flow.md) §7).

## Intentional simplifications

- Analyzer is **rule-based**, not an LLM pipeline in code.
- **feedback-service → mukti-agent** async transport (queue vs poll) is not implemented; tests call Mukti synchronously after feedback submission.
