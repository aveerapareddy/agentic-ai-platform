from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from gateway.dependencies import ExecutionFacadeDep, GatewayState, get_state
from gateway.http_errors import api_error
from gateway.rbac import ExecutionsReadDep
from gateway.tenant_access import assert_execution_visible
from gateway.schemas.responses import TraceResponse

router = APIRouter(prefix="/executions", tags=["trace"])


@router.get("/{execution_id}/trace", response_model=TraceResponse)
def get_trace(
    execution_id: UUID,
    request: Request,
    auth: ExecutionsReadDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> TraceResponse:
    assert_execution_visible(state.repository, execution_id, auth, request=request)
    data = facade.build_trace_projection(execution_id)
    if data is None:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request)
    return TraceResponse.model_validate(data)
