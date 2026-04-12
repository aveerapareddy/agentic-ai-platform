# evaluation-engine

Trace-grounded **metrics** and **aggregates** over persisted executions (Phase 8). This package **does not** run workflows, call models for scoring, or write execution state. It **reads** through `ExecutionDataPort` (typically implemented by the orchestrator repository).

## Alignment

- **Constitution §4.4 / §5.3 / §8.10:** Metrics are derived from stored execution data and trace records; no hidden scoring path.
- **End-state §2.8:** Model fallback share, validation, policy outcomes, tool success, latency-style signals, aggregations by workflow / step / tool / policy, and rule-based anomaly hints.

## Metrics (per execution)

| Field | Source |
|--------|--------|
| `model_fallback_rate` | `execution.trace_timeline` rows with `event_type=model_reasoning`: ratio where `path=deterministic_fallback` to all such events. |
| `validation_success` | Validation-class steps (`StepType.VALIDATION`, planner name containing `validate`, …) via `StepResult.validation_outcome` / step status / `execution.validation_summary`. |
| `policy_decisions` | `list_policy_evaluations_for_execution`, ordered by `created_at`. |
| `policy_outcome` | Final decision in that order (chronological last). |
| `tool_success_rate` | All `ToolCall` rows for the execution’s steps: `ToolCallStatus.SUCCESS` / total. |
| `step_latency_sum_ms` | Sum of `StepResult.latency_ms` where present. |
| `wall_clock_ms` | `completed_at - created_at` when both exist. |
| `total_latency_ms` | `wall_clock_ms` when present; otherwise `step_latency_sum_ms` when any step latency exists; else undefined. |

`ExecutionMetrics.computation_notes` lists how each run was interpreted.

## Aggregations

- **by_workflow_type:** execution counts, failure counts, means of per-execution `model_fallback_rate` and `tool_success_rate` (where defined), policy decision counts.
- **by_step_type:** step counts, success/fail counts, `model_reasoning` / fallback event counts **correlated** to steps via timeline `step_id`.
- **by_tool_name:** invocation and success/failure counts from `ToolCall` rows.
- **by_policy_decision:** evaluation row counts and distinct execution counts.

## Anomaly detection (rule-based)

Thresholds are **constants** in `evaluation_engine/anomalies.py` (documented, not learned):

- High per-execution model fallback rate (with minimum `model_reasoning` events).
- Elevated failure rate within a workflow bucket (minimum execution count).
- High share of `deny` among policy evaluations (minimum evaluation count).

Each finding includes `code`, `severity`, `explanation`, and `evidence` (counts, ids).

## Evaluation score (optional scalar)

`compute_evaluation_score` in `scoring.py` combines mean tool success and `(1 - mean model_fallback_rate)` with a small penalty from execution failure rate. The formula is **fixed and printed** in `EvaluationSummary.score_formula_notes`. It is **not** model-based.

## API

```python
from evaluation_engine import AggregatedMetricFilters, EvaluationService, ExecutionDataPort

svc = EvaluationService(store)  # store implements ExecutionDataPort
m = svc.get_execution_metrics(execution_id)
agg = svc.get_aggregated_metrics(AggregatedMetricFilters(workflow_type="incident_triage", limit=100))
summary = svc.get_evaluation_summary(AggregatedMetricFilters(limit=50))
```

## What is NOT included

- No HTTP server or gateway routes (wire separately).
- No persistence of metric snapshots (recompute from store for reproducibility).
- No ML / LLM scoring.
- No modification of orchestrator behavior.

## Install (local monorepo)

```bash
cd services/evaluation-engine
pip install -e ../../packages/common-schemas -e .
pytest
```

## Example `ExecutionMetrics` (illustrative)

```json
{
  "execution_id": "…",
  "workflow_type": "incident_triage",
  "execution_status": "completed",
  "tenant_id": "t1",
  "model_reasoning_event_count": 4,
  "model_reasoning_fallback_event_count": 1,
  "model_fallback_rate": 0.25,
  "validation_success": true,
  "validation_detail": "aggregated validation step outcomes",
  "policy_decisions": ["conditional"],
  "policy_outcome": "conditional",
  "tool_calls_total": 4,
  "tool_calls_success": 4,
  "tool_success_rate": 1.0,
  "step_latency_sum_ms": 42,
  "wall_clock_ms": 1500,
  "total_latency_ms": 1500,
  "computation_notes": ["…"]
}
```
