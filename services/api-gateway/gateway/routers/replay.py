from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from common_schemas import ReplayCreatedResponse, ReplayDiffSummary

from gateway.dependencies import ExecutionFacadeDep, GatewayState, ReplayDiffFacadeDep, get_state
from fastapi import Depends
from gateway.http_errors import api_error
from gateway.rbac import ExecutionsReadDep, ExecutionsWriteDep
from gateway.tenant_access import assert_execution_visible

from gateway.schemas.requests import ReplayExecutionRequest

router = APIRouter(prefix="/executions", tags=["replay"])


@router.post("/{execution_id}/replay", status_code=202, response_model=ReplayCreatedResponse)
def request_replay(
    execution_id: UUID,
    body: ReplayExecutionRequest,
    request: Request,
    auth: ExecutionsWriteDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> JSONResponse:
    assert_execution_visible(state.repository, execution_id, auth, request=request)
    try:
        created = facade.request_replay(
            execution_id,
            mode=body.mode,
            plan_id=body.plan_id,
            environment_target=body.environment_target,
            label=body.label,
            reason=body.reason,
            requested_by=body.requested_by,
            input_overrides=body.input_overrides,
            start_execution=body.start_execution,
        )
    except KeyError:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request) from None
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e

    return JSONResponse(status_code=202, content=created.model_dump(mode="json"))


@router.get(
    "/{execution_id}/replay-diff/{replay_execution_id}",
    response_model=ReplayDiffSummary,
)
def get_replay_diff(
    execution_id: UUID,
    replay_execution_id: UUID,
    request: Request,
    auth: ExecutionsReadDep,
    facade: ReplayDiffFacadeDep,
    state: GatewayState = Depends(get_state),
) -> ReplayDiffSummary:
    assert_execution_visible(state.repository, execution_id, auth, request=request)
    assert_execution_visible(state.repository, replay_execution_id, auth, request=request)
    try:
        return facade.get_replay_diff(execution_id, replay_execution_id)
    except KeyError:
        raise api_error(
            code="NOT_FOUND",
            message="source or replay execution not found",
            status_code=404,
            request=request,
        ) from None
