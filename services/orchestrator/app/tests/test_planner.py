"""Planner output shape."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import ContextId, Execution, ExecutionId, ExecutionMode, ExecutionStatus

from app.runtime.planner import Planner


def _minimal_execution(workflow_type: str) -> Execution:
    now = datetime.now(timezone.utc)
    eid: ExecutionId = uuid4()
    cid: ContextId = uuid4()
    return Execution(
        execution_id=eid,
        workflow_type=workflow_type,
        status=ExecutionStatus.CREATED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        input={"k": "v"},
        created_at=now,
        updated_at=now,
    )


def test_planner_incident_two_steps() -> None:
    p = Planner()
    plan = p.create_plan(_minimal_execution("incident_triage"))
    assert plan.plan_version == 1
    assert len(plan.steps) == 2
    assert plan.steps[0]["kind"] == "reasoning"
    assert plan.steps[1]["kind"] == "validation"
    assert len(plan.dependencies) == 1


def test_planner_default_two_steps() -> None:
    """Planner is workflow-agnostic: reasoning then validation for all workflows."""
    p = Planner()
    plan = p.create_plan(_minimal_execution("cost_attribution"))
    assert len(plan.steps) == 2
    assert plan.steps[0]["kind"] == "reasoning"
    assert plan.steps[1]["kind"] == "validation"
    assert len(plan.dependencies) == 1
