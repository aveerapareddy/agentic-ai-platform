"""Roll up metrics across many executions (workflow, step type, tool, policy dimensions)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from uuid import UUID

from common_schemas import Execution, Step, StepStatus, ToolCallStatus

from evaluation_engine.models import (
    AggregatedMetrics,
    ExecutionMetrics,
    PolicyDecisionRollup,
    StepTypeRollup,
    ToolNameRollup,
    WorkflowTypeRollup,
)


def _step_type_key(step: Step) -> str:
    st = step.step_type
    if hasattr(st, "value"):
        return str(st.value)
    return str(st)


def aggregate_from_execution_metrics(
    per_execution: list[ExecutionMetrics],
) -> AggregatedMetrics:
    """Roll up pre-computed ExecutionMetrics by workflow and policy."""
    by_wf: dict[str, list[ExecutionMetrics]] = defaultdict(list)
    by_pol: dict[str, list[str]] = defaultdict(list)

    for m in per_execution:
        by_wf[m.workflow_type].append(m)
        for d in m.policy_decisions:
            by_pol[d].append(m.execution_id)

    wf_roll: dict[str, WorkflowTypeRollup] = {}
    for wf, rows in by_wf.items():
        n = len(rows)
        failed = sum(1 for r in rows if r.execution_status == "failed")
        fb_rates = [r.model_fallback_rate for r in rows if r.model_fallback_rate is not None]
        mean_fb = sum(fb_rates) / len(fb_rates) if fb_rates else None
        tr = [r.tool_success_rate for r in rows if r.tool_success_rate is not None]
        mean_tr = sum(tr) / len(tr) if tr else None
        pol_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            for d in r.policy_decisions:
                pol_counts[d] += 1
        wf_roll[wf] = WorkflowTypeRollup(
            execution_count=n,
            failed_execution_count=failed,
            mean_model_fallback_rate=mean_fb,
            mean_tool_success_rate=mean_tr,
            policy_decision_counts=dict(pol_counts),
        )

    pol_roll: dict[str, PolicyDecisionRollup] = {}
    for dec, exec_ids in by_pol.items():
        pol_roll[dec] = PolicyDecisionRollup(
            evaluation_count=sum(1 for m in per_execution for d in m.policy_decisions if d == dec),
            distinct_execution_count=len(set(exec_ids)),
        )

    return AggregatedMetrics(
        executions_in_scope=len(per_execution),
        by_workflow_type=wf_roll,
        by_step_type={},
        by_tool_name={},
        by_policy_decision=pol_roll,
    )


def extend_with_step_and_tool_dimensions(
    base: AggregatedMetrics,
    *,
    executions: list[Execution],
    steps_by_execution: dict[str, list[Step]],
    tool_calls_by_execution: dict[str, list],
) -> AggregatedMetrics:
    """Add step_type (trace-correlated model_reasoning) and tool_name rollups."""

    st_rollup: dict[str, StepTypeRollup] = {}

    def get_st(key: str) -> StepTypeRollup:
        if key not in st_rollup:
            st_rollup[key] = StepTypeRollup(
                step_count=0,
                succeeded=0,
                failed=0,
                model_reasoning_events=0,
                model_fallback_events=0,
            )
        return st_rollup[key]

    for ex in executions:
        eid = str(ex.execution_id)
        steps = steps_by_execution.get(eid, [])
        by_sid = {s.step_id: s for s in steps}

        for s in steps:
            r = get_st(_step_type_key(s))
            r.step_count += 1
            if s.status == StepStatus.SUCCEEDED:
                r.succeeded += 1
            elif s.status == StepStatus.FAILED:
                r.failed += 1

        for ev in ex.trace_timeline or []:
            if ev.get("event_type") != "model_reasoning":
                continue
            sid_raw = ev.get("step_id")
            if sid_raw is None:
                continue
            try:
                uid = UUID(str(sid_raw))
            except (ValueError, TypeError):
                continue
            step = by_sid.get(uid)
            if step is None:
                continue
            r = get_st(_step_type_key(step))
            r.model_reasoning_events += 1
            if ev.get("path") == "deterministic_fallback":
                r.model_fallback_events += 1

    tool_rollup: dict[str, ToolNameRollup] = defaultdict(
        lambda: ToolNameRollup(invocations=0, successes=0, failures=0)
    )
    for ex in executions:
        eid = str(ex.execution_id)
        for tc in tool_calls_by_execution.get(eid, []):
            name = getattr(tc, "tool_name", "") or "unknown"
            t = tool_rollup[name]
            t.invocations += 1
            if tc.status == ToolCallStatus.SUCCESS:
                t.successes += 1
            else:
                t.failures += 1

    base.by_step_type = dict(st_rollup)
    base.by_tool_name = dict(tool_rollup)
    return base


def build_full_aggregated_metrics(
    per_execution: list[ExecutionMetrics],
    executions: list[Execution],
    load_steps: Callable[[UUID], list[Step]],
    load_tools: Callable[[list[Step]], list],
) -> AggregatedMetrics:
    base = aggregate_from_execution_metrics(per_execution)
    steps_by_execution: dict[str, list[Step]] = {}
    tool_by_e: dict[str, list] = {}
    for ex in executions:
        eid = ex.execution_id
        steps = load_steps(eid)
        steps_by_execution[str(eid)] = steps
        tool_by_e[str(eid)] = load_tools(steps)
    return extend_with_step_and_tool_dimensions(
        base,
        executions=executions,
        steps_by_execution=steps_by_execution,
        tool_calls_by_execution=tool_by_e,
    )
