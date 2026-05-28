from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from gateway.context_merge import merge_execution_context
from gateway.dependencies import ExecutionFacadeDep, GatewayState, get_state
from gateway.http_errors import api_error
from gateway.rbac import ExecutionsReadDep, ExecutionsWriteDep
from gateway.tenant_access import assert_execution_visible
from gateway.schemas.requests import CreateExecutionRequest
from gateway.schemas.responses import (
    CreateExecutionResponse,
    ExecutionDetailResponse,
    ExecutionListItem,
    ListExecutionsResponse,
)
router = APIRouter(prefix="/executions", tags=["executions"])


def _to_detail(ex) -> ExecutionDetailResponse:
    return ExecutionDetailResponse(
        execution_id=ex.execution_id,
        workflow_type=ex.workflow_type,
        status=ex.status.value,
        execution_context_id=ex.execution_context_id,
        current_plan_id=ex.current_plan_id,
        parent_execution_id=ex.parent_execution_id,
        input=dict(ex.input),
        result=dict(ex.result) if ex.result is not None else None,
        validation_summary=dict(ex.validation_summary) if ex.validation_summary is not None else None,
        created_at=ex.created_at,
        updated_at=ex.updated_at,
        completed_at=ex.completed_at,
        cancelled_at=ex.cancelled_at,
    )


@router.post("", status_code=201, response_model=CreateExecutionResponse)
def create_execution(
    body: CreateExecutionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth: ExecutionsWriteDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> CreateExecutionResponse:
    try:

        def _schedule_start(eid: UUID) -> None:
            background_tasks.add_task(state.execution_service.start_execution, eid)

        start_cb = _schedule_start if state.settings.schedule_execution_start else None
        ctx = merge_execution_context(dict(body.context), auth)
        if body.execution_mode is not None:
            ctx["execution_mode"] = body.execution_mode
        ex = facade.create_execution(
            workflow_type=body.workflow_type,
            input_payload=dict(body.input),
            context=ctx,
            idempotency_key=body.idempotency_key,
            schedule_start=state.settings.schedule_execution_start,
            start_callback=start_cb,
        )
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e

    return CreateExecutionResponse(
        execution_id=ex.execution_id,
        status=ex.status.value,
        workflow_type=ex.workflow_type,
        created_at=ex.created_at,
        links={"self": f"/v1/executions/{ex.execution_id}"},
    )


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(
    execution_id: UUID,
    request: Request,
    auth: ExecutionsReadDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> ExecutionDetailResponse:
    ex = assert_execution_visible(state.repository, execution_id, auth, request=request)
    return _to_detail(ex)


@router.get("", response_model=ListExecutionsResponse)
def list_executions(
    request: Request,
    auth: ExecutionsReadDep,
    facade: ExecutionFacadeDep,
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> ListExecutionsResponse:
    scoped_tenant = auth.tenant.tenant_id
    if tenant_id is not None and tenant_id != scoped_tenant:
        raise api_error(
            code="FORBIDDEN",
            message="tenant_id query must match authenticated tenant",
            status_code=403,
            request=request,
        )
    rows = facade.list_executions(
        tenant_id=scoped_tenant,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
    items = [
        ExecutionListItem(
            execution_id=e.execution_id,
            status=e.status.value,
            workflow_type=e.workflow_type,
            created_at=e.created_at,
        )
        for e in rows
    ]
    return ListExecutionsResponse(items=items, next_cursor=None)


@router.post("/{execution_id}/cancel", response_model=ExecutionDetailResponse)
def cancel_execution(
    execution_id: UUID,
    request: Request,
    auth: ExecutionsWriteDep,
    facade: ExecutionFacadeDep,
    state: GatewayState = Depends(get_state),
) -> ExecutionDetailResponse:
    assert_execution_visible(state.repository, execution_id, auth, request=request)
    try:
        ex = facade.request_cancellation(execution_id, reason="api_request")
    except KeyError as e:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request) from e
    return _to_detail(ex)
