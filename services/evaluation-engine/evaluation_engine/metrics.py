"""Per-execution metric computation from persisted rows and trace timeline."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timezone
from uuid import UUID

from common_schemas import (
    Execution,
    PolicyEvaluation,
    Step,
    StepResult,
    StepStatus,
    StepType,
    ToolCall,
    ToolCallStatus,
)

from evaluation_engine.models import ExecutionMetrics


def _planner_name(step: Step) -> str | None:
    raw = step.input.get("planner_step_name")
    return str(raw) if isinstance(raw, str) else None


def _is_validation_like_step(step: Step) -> bool:
    st = step.step_type
    if st == StepType.VALIDATION:
        return True
    if isinstance(st, str) and st.lower() == "validation":
        return True
    name = _planner_name(step)
    if name and "validate" in name.lower():
        return True
    return False


def _validation_success_from_results(
    steps: list[Step],
    results: dict[UUID, StepResult],
    validation_summary: dict | None,
) -> tuple[bool | None, str | None]:
    vsteps = [s for s in steps if _is_validation_like_step(s)]
    if not vsteps:
        if validation_summary:
            status = validation_summary.get("status") or validation_summary.get("overall")
            if isinstance(status, str):
                sl = status.lower()
                if sl in ("passed", "success", "ok", "complete"):
                    return True, "validation_summary.status"
                if sl in ("failed", "fail", "error"):
                    return False, "validation_summary.status"
            return None, "validation_summary present but no explicit status"
        return None, "no validation-class step or validation_summary"

    outcomes: list[bool] = []
    for s in vsteps:
        sr = results.get(s.step_id)
        if sr is None:
            continue
        if sr.validation_outcome is not None:
            st = str(sr.validation_outcome.status).lower()
            if st in ("passed", "success", "ok"):
                outcomes.append(True)
            elif st in ("failed", "fail", "error", "inconclusive"):
                outcomes.append(False)
            else:
                outcomes.append(False)
        elif s.status == StepStatus.FAILED:
            outcomes.append(False)
        elif s.status == StepStatus.SUCCEEDED and isinstance(sr.output, dict):
            vs = sr.output.get("validation_status")
            if isinstance(vs, str) and vs.lower() in ("passed", "success", "ok"):
                outcomes.append(True)
            elif isinstance(vs, str):
                outcomes.append(False)

    if not outcomes:
        return None, "validation steps present but no outcomes recorded"

    return (all(outcomes), "aggregated validation step outcomes")


def _model_reasoning_counts(timeline: list[dict]) -> tuple[int, int]:
    events = [e for e in timeline if e.get("event_type") == "model_reasoning"]
    total = len(events)
    fallbacks = sum(1 for e in events if e.get("path") == "deterministic_fallback")
    return total, fallbacks


def _wall_clock_ms(execution: Execution) -> int | None:
    if execution.completed_at is None:
        return None
    start = execution.created_at
    end = execution.completed_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    delta = end - start
    return int(delta.total_seconds() * 1000)


def compute_execution_metrics(
    execution: Execution,
    *,
    steps: list[Step],
    step_results: dict[UUID, StepResult],
    tool_calls: list[ToolCall],
    policy_evaluations: list[PolicyEvaluation],
    tenant_id: str | None = None,
) -> ExecutionMetrics:
    notes: list[str] = []
    timeline = list(execution.trace_timeline or [])
    mr_total, mr_fb = _model_reasoning_counts(timeline)
    fb_rate: float | None
    if mr_total == 0:
        fb_rate = None
        notes.append("model_fallback_rate undefined: no model_reasoning timeline events")
    else:
        fb_rate = mr_fb / mr_total
        notes.append(
            "model_fallback_rate = count(model_reasoning with path=deterministic_fallback) / "
            "count(model_reasoning events)"
        )

    val_ok, val_detail = _validation_success_from_results(
        steps,
        step_results,
        execution.validation_summary,
    )
    if val_detail:
        notes.append(f"validation_success: {val_detail}")

    evals = sorted(policy_evaluations, key=lambda e: e.created_at)
    decisions = [e.decision.value for e in evals]
    primary = decisions[-1] if decisions else None
    if evals:
        notes.append("policy_decisions ordered by policy_evaluation.created_at")

    tc_total = len(tool_calls)
    tc_ok = sum(1 for t in tool_calls if t.status == ToolCallStatus.SUCCESS)
    tool_rate = (tc_ok / tc_total) if tc_total else None
    if tc_total:
        notes.append("tool_success_rate uses ToolCallStatus.SUCCESS vs all tool_calls rows")

    lat_sum = 0
    lat_any = False
    for s in steps:
        sr = step_results.get(s.step_id)
        if sr is not None and sr.latency_ms is not None:
            lat_sum += int(sr.latency_ms)
            lat_any = True

    wc = _wall_clock_ms(execution)
    if wc is not None:
        notes.append("wall_clock_ms = completed_at - created_at")

    step_sum = lat_sum if lat_any else None
    if wc is not None:
        total_lat = wc
        notes.append(
            "total_latency_ms = wall_clock_ms (execution completed_at present; preferred over step sum)"
        )
    elif step_sum is not None:
        total_lat = step_sum
        notes.append(
            "total_latency_ms = step_latency_sum_ms (no completed_at wall clock; sum of StepResult.latency_ms)"
        )
    else:
        total_lat = None
        notes.append("total_latency_ms undefined: no wall clock and no step latencies")

    return ExecutionMetrics(
        execution_id=str(execution.execution_id),
        workflow_type=execution.workflow_type,
        execution_status=execution.status.value,
        tenant_id=tenant_id,
        model_reasoning_event_count=mr_total,
        model_reasoning_fallback_event_count=mr_fb,
        model_fallback_rate=fb_rate,
        validation_success=val_ok,
        validation_detail=val_detail,
        policy_decisions=decisions,
        policy_outcome=primary,
        tool_calls_total=tc_total,
        tool_calls_success=tc_ok,
        tool_success_rate=tool_rate,
        step_latency_sum_ms=step_sum,
        wall_clock_ms=wc,
        total_latency_ms=total_lat,
        computation_notes=notes,
    )


def load_tool_calls_for_execution(
    steps: list[Step],
    list_tool_calls_for_step: Callable[[UUID], list[ToolCall]],
) -> list[ToolCall]:
    out: list[ToolCall] = []
    for s in steps:
        out.extend(list_tool_calls_for_step(s.step_id))
    return out
