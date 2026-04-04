"""Phase 3 governance: policy branches and approval for incident_triage."""

from __future__ import annotations

from uuid import UUID

from common_schemas import ApprovalDecision, ExecutionStatus, PolicyDecision

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService


def _svc() -> tuple[ExecutionService, InMemoryRepository]:
    repo = InMemoryRepository()
    return ExecutionService(repo), repo


def test_policy_deny_path_fails_execution() -> None:
    svc, repo = _svc()
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "x"},
        tenant_id="t1",
        request_id="r1",
        environment="dev",
        policy_scope="phase3_deny",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.FAILED
    assert done.result is not None
    assert done.result.get("policy_decision") == PolicyDecision.DENY.value
    assert done.result.get("outcome") == "failed"
    pid = done.result.get("proposed_action", {}).get("proposal_id")
    assert pid
    prop = repo.get_action_proposal(UUID(pid))
    assert prop is not None
    assert prop.status.value == "policy_denied"
    assert any(r.get("event_type") == "policy_evaluated" for r in done.trace_timeline)


def test_policy_conditional_awaiting_approval_then_approve() -> None:
    svc, repo = _svc()
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "y"},
        tenant_id="t1",
        request_id="r1",
        environment="dev",
        policy_scope="phase3_conditional",
    )
    paused = svc.start_execution(ex.execution_id)
    assert paused.status == ExecutionStatus.AWAITING_APPROVAL
    assert paused.result.get("outcome") == "awaiting_approval"
    assert paused.result.get("approval_status") == "pending"
    assert any(r.get("event_type") == "approval_required" for r in paused.trace_timeline)

    done = svc.submit_approval(
        ex.execution_id,
        approver="operator-1",
        decision=ApprovalDecision.APPROVE,
    )
    assert done.status == ExecutionStatus.COMPLETED
    assert done.result.get("approval_status") == "approved"
    assert done.result.get("policy_decision") == PolicyDecision.CONDITIONAL.value
    assert any(r.get("event_type") == "approval_received" for r in done.trace_timeline)


def test_policy_conditional_reject_fails() -> None:
    svc, _repo = _svc()
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "z"},
        tenant_id="t1",
        request_id="r1",
        environment="dev",
        policy_scope="phase3_conditional",
    )
    svc.start_execution(ex.execution_id)
    done = svc.submit_approval(
        ex.execution_id,
        approver="operator-2",
        decision=ApprovalDecision.REJECT,
    )
    assert done.status == ExecutionStatus.FAILED
    assert done.result.get("approval_status") == "rejected"


def test_prod_environment_triggers_conditional() -> None:
    svc, _ = _svc()
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "p"},
        tenant_id="t1",
        request_id="r1",
        environment="prod",
        policy_scope="default",
    )
    paused = svc.start_execution(ex.execution_id)
    assert paused.status == ExecutionStatus.AWAITING_APPROVAL
