"""End-to-end execution through ExecutionService."""

from __future__ import annotations

from common_schemas import ExecutionStatus

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService


def test_happy_path_incident_workflow() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "1"},
        tenant_id="t1",
        request_id="r1",
        environment="dev",
        policy_scope="p1",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    assert done.result is not None
    assert done.result.get("outcome") == "success"
    assert done.validation_summary is not None
    assert done.validation_summary.get("recorded") is True
    assert any(
        row.get("status") == ExecutionStatus.VALIDATING.value
        for row in done.trace_timeline
        if row.get("event_type") == "execution_status"
    )
    steps = repo.list_steps_for_execution(ex.execution_id)
    assert len(steps) == 2


def test_happy_path_default_workflow() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="generic",
        input_payload={},
        tenant_id="t1",
        request_id="r1",
        environment="dev",
        policy_scope="p1",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    assert len(repo.list_steps_for_execution(ex.execution_id)) == 2
