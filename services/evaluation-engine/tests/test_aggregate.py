from uuid import uuid4

from common_schemas import (
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionStatus,
    Step,
    StepStatus,
    StepType,
    ToolCall,
    ToolCallStatus,
    ToolIdempotency,
    ToolSideEffectClass,
)

from evaluation_engine.aggregate import aggregate_from_execution_metrics, build_full_aggregated_metrics
from evaluation_engine.models import ExecutionMetrics
from tests.conftest import FakeStore, utc


def test_aggregate_workflow_and_policy() -> None:
    m1 = ExecutionMetrics(
        execution_id="a",
        workflow_type="incident_triage",
        execution_status="completed",
        model_reasoning_event_count=2,
        model_reasoning_fallback_event_count=0,
        model_fallback_rate=0.0,
        tool_calls_total=1,
        tool_calls_success=1,
        tool_success_rate=1.0,
        policy_decisions=["allow"],
    )
    m2 = ExecutionMetrics(
        execution_id="b",
        workflow_type="incident_triage",
        execution_status="failed",
        model_reasoning_event_count=2,
        model_reasoning_fallback_event_count=2,
        model_fallback_rate=1.0,
        tool_calls_total=0,
        tool_calls_success=0,
        tool_success_rate=None,
        policy_decisions=["deny"],
    )
    agg = aggregate_from_execution_metrics([m1, m2])
    assert agg.executions_in_scope == 2
    assert "incident_triage" in agg.by_workflow_type
    wf = agg.by_workflow_type["incident_triage"]
    assert wf.execution_count == 2
    assert wf.failed_execution_count == 1
    assert wf.mean_model_fallback_rate == 0.5
    assert agg.by_policy_decision["allow"].evaluation_count == 1
    assert agg.by_policy_decision["deny"].distinct_execution_count == 1


def test_build_full_aggregated_step_and_tool_dimensions() -> None:
    store = FakeStore()
    eid = uuid4()
    cid = uuid4()
    sid = uuid4()
    now = utc()
    store.contexts[cid] = ExecutionContext(
        context_id=cid,
        tenant_id="t1",
        request_id="r",
        environment="dev",
        policy_scope="p",
        created_at=now,
        updated_at=now,
    )
    ex = Execution(
        execution_id=eid,
        workflow_type="wf",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[
            {
                "event_type": "model_reasoning",
                "path": "deterministic_fallback",
                "step_id": str(sid),
                "at": now.isoformat(),
            },
        ],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    store.executions[eid] = ex
    step = Step(
        step_id=sid,
        execution_id=eid,
        plan_id=uuid4(),
        step_type=StepType.REASONING,
        agent="a",
        input={},
        status=StepStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    store.steps[eid] = [step]
    tc = ToolCall(
        tool_call_id=uuid4(),
        execution_id=eid,
        step_id=sid,
        execution_context_id=cid,
        tool_name="incident_metadata_tool",
        side_effect_class=ToolSideEffectClass.READ_ONLY,
        idempotency=ToolIdempotency.IDEMPOTENT,
        status=ToolCallStatus.SUCCESS,
        created_at=now,
        updated_at=now,
    )
    store.tool_calls[sid] = [tc]

    from evaluation_engine.metrics import compute_execution_metrics, load_tool_calls_for_execution
    from evaluation_engine.service import EvaluationService

    svc = EvaluationService(store)
    m = svc.get_execution_metrics(eid)
    assert m is not None

    def load_steps(eid_inner):
        return store.list_steps_for_execution(eid_inner)

    def load_tools(steps):
        return load_tool_calls_for_execution(steps, store.list_tool_calls_for_step)

    agg = build_full_aggregated_metrics([m], [ex], load_steps, load_tools)
    assert "reasoning" in agg.by_step_type or str(StepType.REASONING.value) in agg.by_step_type
    st_key = StepType.REASONING.value
    assert agg.by_step_type[st_key].model_reasoning_events == 1
    assert agg.by_step_type[st_key].model_fallback_events == 1
    assert "incident_metadata_tool" in agg.by_tool_name
    assert agg.by_tool_name["incident_metadata_tool"].successes == 1
