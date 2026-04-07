from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gateway.dependencies import ExecutionFacadeDep
from gateway.http_errors import api_error
from gateway.schemas.requests import ReplayExecutionRequest
from gateway.schemas.responses import ReplayAcceptedResponse

router = APIRouter(prefix="/executions", tags=["replay"])


@router.post("/{execution_id}/replay", status_code=202)
def request_replay(
    execution_id: UUID,
    body: ReplayExecutionRequest,
    request: Request,
    facade: ExecutionFacadeDep,
) -> JSONResponse:
    try:
        child = facade.request_replay(
            execution_id,
            mode=body.mode,
            plan_id=body.plan_id,
            environment_target=body.environment_target,
            label=body.label,
        )
    except KeyError:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request) from None
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e

    payload = ReplayAcceptedResponse(
        replay_execution_id=child.execution_id,
        source_execution_id=execution_id,
        status=child.status.value,
        mode=body.mode,
    )
    return JSONResponse(status_code=202, content=payload.model_dump(mode="json"))
