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
    assert done.result.get("workflow_type") == "incident_triage"
    assert done.result.get("policy_decision") == "allow"
    assert done.result.get("approval_status") == "not_required"
    assert done.result.get("proposed_action", {}).get("type") == "escalate_incident"
    assert "incident_summary" in done.result
    assert done.result.get("incident_summary")
    assert done.result.get("likely_cause") in (
        "config_drift",
        "dependency_failure",
        "capacity_saturation",
    )
    assert done.result.get("evidence_summary")
    assert done.result.get("validation_status") == "passed"
    assert done.result.get("confidence_score") is not None
    assert done.validation_summary is not None
    assert done.validation_summary.get("recorded") is True
    assert any(
        row.get("status") == ExecutionStatus.VALIDATING.value
        for row in done.trace_timeline
        if row.get("event_type") == "execution_status"
    )
    started = [r for r in done.trace_timeline if r.get("event_type") == "step_started"]
    completed = [r for r in done.trace_timeline if r.get("event_type") == "step_completed"]
    validations = [r for r in done.trace_timeline if r.get("event_type") == "validation_performed"]
    assert len(started) == 3
    assert len(completed) == 3
    assert len(validations) == 1
    assert validations[0].get("validation_status") == "passed"
    assert any(r.get("event_type") == "knowledge_retrieved" for r in done.trace_timeline)
    assert len([r for r in done.trace_timeline if r.get("event_type") == "tool_call_completed"]) >= 2
    model_paths = [
        r.get("path")
        for r in done.trace_timeline
        if r.get("event_type") == "model_reasoning" and r.get("path") == "model_runtime"
    ]
    assert len(model_paths) >= 2
    assert any(r.get("event_type") == "action_proposed" for r in done.trace_timeline)
    assert any(r.get("event_type") == "policy_evaluated" for r in done.trace_timeline)
    assert any(r.get("event_type") == "governed_outcome" for r in done.trace_timeline)
    steps = repo.list_steps_for_execution(ex.execution_id)
    assert len(steps) == 3


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
    assert done.result == {"outcome": "success", "steps": 2}
    assert not any(r.get("event_type") == "step_status" for r in done.trace_timeline)
