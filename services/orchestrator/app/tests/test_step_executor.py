"""Simulated step execution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import ExecutionId, PlanId, Step, StepId, StepStatus, StepType

from app.runtime.step_executor import StepExecutor


def _step(kind: StepType, *, status: StepStatus = StepStatus.RUNNING) -> Step:
    now = datetime.now(timezone.utc)
    sid: StepId = uuid4()
    eid: ExecutionId = uuid4()
    pid: PlanId = uuid4()
    return Step(
        step_id=sid,
        execution_id=eid,
        plan_id=pid,
        step_type=kind,
        agent="test",
        input={},
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_step_executor_reasoning_output() -> None:
    ex = StepExecutor()
    s = _step(StepType.REASONING)
    r = ex.execute_step(s)
    assert r.confidence_score == pytest.approx(0.82)
    assert r.output is not None
    assert "reasoning_digest" in r.output


def test_step_executor_validation_output() -> None:
    ex = StepExecutor()
    s = _step(StepType.VALIDATION)
    r = ex.execute_step(s)
    assert r.confidence_score == pytest.approx(0.95)
    assert r.output is not None
    assert r.output.get("validated") is True


def test_step_executor_requires_running() -> None:
    ex = StepExecutor()
    s = _step(StepType.REASONING, status=StepStatus.PENDING)
    with pytest.raises(ValueError, match="RUNNING"):
        ex.execute_step(s)


def _incident_step(
    step_type: StepType,
    step_name: str,
    *,
    execution_input: dict | None = None,
) -> Step:
    now = datetime.now(timezone.utc)
    sid: StepId = uuid4()
    eid: ExecutionId = uuid4()
    pid: PlanId = uuid4()
    return Step(
        step_id=sid,
        execution_id=eid,
        plan_id=pid,
        step_type=step_type,
        agent="test",
        input={
            "workflow_type": "incident_triage",
            "planner_step_name": step_name,
            "execution_input": execution_input or {"incident_id": "inc-42"},
        },
        status=StepStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )


def test_step_executor_incident_analyze_structured() -> None:
    ex = StepExecutor()
    s = _incident_step(StepType.REASONING, "analyze_incident")
    r = ex.execute_step(s)
    assert r.output is not None
    assert "incident_summary" in r.output
    assert "possible_causes" in r.output
    assert isinstance(r.output["possible_causes"], list)


def test_step_executor_incident_gather_structured() -> None:
    ex = StepExecutor()
    s = _incident_step(StepType.RETRIEVAL, "gather_evidence")
    r = ex.execute_step(s)
    assert r.output is not None
    assert "evidence_summary" in r.output
    assert "signals" in r.output
    assert isinstance(r.output["signals"], list)


def test_step_executor_incident_validate_structured() -> None:
    ex = StepExecutor()
    s = _incident_step(StepType.VALIDATION, "validate_incident")
    r = ex.execute_step(s)
    assert r.output is not None
    assert r.output.get("likely_cause")
    assert r.output.get("validation_status") == "passed"
    assert r.output.get("confidence_score") is not None
    assert r.validation_outcome is not None
