from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from gateway._bootstrap import ensure_platform_paths
from gateway.dependencies import ExecutionFacadeDep, GatewayState, get_state
from fastapi import Depends
from gateway.http_errors import api_error
from gateway.rbac import ApprovalsWriteDep
from gateway.tenant_access import assert_execution_visible
from gateway.schemas.requests import SubmitApprovalRequest
from gateway.schemas.responses import ApprovalCreatedResponse

ensure_platform_paths()

from app.runtime.orchestrator import OrchestrationError

router = APIRouter(prefix="/executions", tags=["approvals"])


@router.post("/{execution_id}/approvals", status_code=201, response_model=ApprovalCreatedResponse)
def submit_approval(
    execution_id: UUID,
    body: SubmitApprovalRequest,
    request: Request,
    _auth: ApprovalsWriteDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> ApprovalCreatedResponse:
    assert_execution_visible(state.repository, execution_id, _auth, request=request)
    try:
        approval = facade.submit_approval(
            execution_id,
            action_proposal_id=body.action_proposal_id,
            policy_evaluation_id=body.policy_evaluation_id,
            decision=body.decision,
            approver=body.approver,
            notes=body.notes,
        )
    except KeyError:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request) from None
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e
    except OrchestrationError as e:
        raise api_error(code="CONFLICT", message=str(e), status_code=409, request=request) from e

    return ApprovalCreatedResponse(
        approval_id=approval.approval_id,
        execution_id=approval.execution_id,
        decision=approval.decision.value,
        decided_at=approval.decided_at,
    )
