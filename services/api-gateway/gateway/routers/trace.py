from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from gateway.dependencies import ExecutionFacadeDep
from gateway.http_errors import api_error
from gateway.schemas.responses import TraceResponse

router = APIRouter(prefix="/executions", tags=["trace"])


@router.get("/{execution_id}/trace", response_model=TraceResponse)
def get_trace(
    execution_id: UUID,
    request: Request,
    facade: ExecutionFacadeDep,
) -> TraceResponse:
    data = facade.build_trace_projection(execution_id)
    if data is None:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request)
    return TraceResponse.model_validate(data)
