from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from gateway.dependencies import ExecutionFacadeDep, GatewayState, get_state
from gateway.http_errors import api_error
from gateway.rbac import ExecutionsReadDep
from gateway.streaming.sse import stream_execution_sse
from gateway.tenant_access import assert_execution_visible

router = APIRouter(prefix="/executions", tags=["stream"])


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: UUID,
    request: Request,
    auth: ExecutionsReadDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> StreamingResponse:
    assert_execution_visible(state.repository, execution_id, auth, request=request)

    if facade.get_execution(execution_id) is None:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request)

    generator = stream_execution_sse(
        facade=facade,
        repository=state.repository,
        execution_id=execution_id,
        auth=auth,
        settings=state.settings,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
