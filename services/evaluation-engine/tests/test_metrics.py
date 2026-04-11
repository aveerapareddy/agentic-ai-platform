from uuid import uuid4

from common_schemas import (
    Execution,
    ExecutionMode,
    ExecutionStatus,
    PolicyDecision,
    PolicyEvaluation,
    Step,
    StepResult,
    StepStatus,
    StepType,
    ToolCall,
    ToolCallStatus,
    ToolIdempotency,
    ToolSideEffectClass,
    ValidationOutcome,
)

from evaluation_engine.metrics import compute_execution_metrics
from tests.conftest import utc


def test_model_fallback_rate_from_timeline() -> None:
    eid = uuid4()
    cid = uuid4()
    sid = uuid4()
    now = utc()
    ex = Execution(
        execution_id=eid,
        workflow_type="incident_triage",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[
            {"event_type": "model_reasoning", "path": "model_runtime", "step_id": str(sid), "at": now.isoformat()},
            {"event_type": "model_reasoning", "path": "deterministic_fallback", "step_id": str(sid), "at": now.isoformat()},
            {"event_type": "model_reasoning", "path": "model_runtime", "at": now.isoformat()},
        ],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    step = Step(
        step_id=sid,
        execution_id=eid,
        plan_id=uuid4(),
        step_type=StepType.REASONING,
        agent="a",
        input={"planner_step_name": "analyze_incident"},
        status=StepStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    sr = StepResult(
        step_result_id=uuid4(),
        step_id=sid,
        latency_ms=10,
        created_at=now,
        updated_at=now,
    )
    m = compute_execution_metrics(
        ex,
        steps=[step],
        step_results={sid: sr},
        tool_calls=[],
        policy_evaluations=[],
    )
    assert m.model_reasoning_event_count == 3
    assert m.model_reasoning_fallback_event_count == 1
    assert abs(m.model_fallback_rate - 1 / 3) < 1e-9


def test_tool_success_rate() -> None:
    eid = uuid4()
    cid = uuid4()
    sid = uuid4()
    now = utc()
    ex = Execution(
        execution_id=eid,
        workflow_type="generic",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    step = Step(
        step_id=sid,
        execution_id=eid,
        plan_id=uuid4(),
        step_type=StepType.TOOL,
        agent="a",
        input={},
        status=StepStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    tc1 = ToolCall(
        tool_call_id=uuid4(),
        execution_id=eid,
        step_id=sid,
        execution_context_id=cid,
        tool_name="t1",
        side_effect_class=ToolSideEffectClass.READ_ONLY,
        idempotency=ToolIdempotency.IDEMPOTENT,
        status=ToolCallStatus.SUCCESS,
        created_at=now,
        updated_at=now,
    )
    tc2 = ToolCall(
        tool_call_id=uuid4(),
        execution_id=eid,
        step_id=sid,
        execution_context_id=cid,
        tool_name="t1",
        side_effect_class=ToolSideEffectClass.READ_ONLY,
        idempotency=ToolIdempotency.IDEMPOTENT,
        status=ToolCallStatus.FAILURE,
        created_at=now,
        updated_at=now,
    )
    m = compute_execution_metrics(
        ex,
        steps=[step],
        step_results={},
        tool_calls=[tc1, tc2],
        policy_evaluations=[],
    )
    assert m.tool_calls_total == 2
    assert m.tool_calls_success == 1
    assert m.tool_success_rate == 0.5


def test_policy_decisions_ordered() -> None:
    eid = uuid4()
    cid = uuid4()
    now = utc()
    ex = Execution(
        execution_id=eid,
        workflow_type="incident_triage",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    pe1 = PolicyEvaluation(
        evaluation_id=uuid4(),
        execution_id=eid,
        execution_context_id=cid,
        decision=PolicyDecision.CONDITIONAL,
        reason="r1",
        created_at=now,
        updated_at=now,
    )
    pe2 = PolicyEvaluation(
        evaluation_id=uuid4(),
        execution_id=eid,
        execution_context_id=cid,
        decision=PolicyDecision.ALLOW,
        reason="r2",
        created_at=now,
        updated_at=now,
    )
    m = compute_execution_metrics(
        ex,
        steps=[],
        step_results={},
        tool_calls=[],
        policy_evaluations=[pe1, pe2],
    )
    assert m.policy_decisions == ["conditional", "allow"]
    assert m.primary_policy_decision == "allow"


def test_validation_success_from_validation_outcome() -> None:
    eid = uuid4()
    cid = uuid4()
    sid = uuid4()
    now = utc()
    ex = Execution(
        execution_id=eid,
        workflow_type="incident_triage",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    step = Step(
        step_id=sid,
        execution_id=eid,
        plan_id=uuid4(),
        step_type=StepType.VALIDATION,
        agent="a",
        input={"planner_step_name": "validate_incident"},
        status=StepStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    sr = StepResult(
        step_result_id=uuid4(),
        step_id=sid,
        validation_outcome=ValidationOutcome(status="passed", details={}),
        created_at=now,
        updated_at=now,
    )
    m = compute_execution_metrics(
        ex,
        steps=[step],
        step_results={sid: sr},
        tool_calls=[],
        policy_evaluations=[],
    )
    assert m.validation_success is True
