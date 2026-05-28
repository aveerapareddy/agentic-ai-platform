from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from gateway.dependencies import MuktiFacadeDep
from gateway.http_errors import api_error
from gateway.rbac import InsightsReadDep
from gateway.schemas.mukti import CrossExecutionInsightResponse, MuktiInsightsSummaryResponse

router = APIRouter(tags=["insights"])


def _scoped_tenant_id(request: Request, auth: InsightsReadDep, tenant_id: str | None) -> str:
    scoped = auth.tenant.tenant_id
    if tenant_id is not None and tenant_id != scoped:
        raise api_error(
            code="FORBIDDEN",
            message="tenant_id query must match authenticated tenant",
            status_code=403,
            request=request,
        )
    return scoped


@router.get("/insights/mukti", response_model=MuktiInsightsSummaryResponse)
def get_mukti_insights(
    request: Request,
    auth: InsightsReadDep,
    facade: MuktiFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> MuktiInsightsSummaryResponse:
    scoped = _scoped_tenant_id(request, auth, tenant_id)
    return facade.get_mukti_insights(
        tenant_id=scoped,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )


@router.get("/insights/mukti/{insight_id}", response_model=CrossExecutionInsightResponse)
def get_mukti_insight(
    insight_id: UUID,
    request: Request,
    auth: InsightsReadDep,
    facade: MuktiFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> CrossExecutionInsightResponse:
    scoped = _scoped_tenant_id(request, auth, tenant_id)
    ins = facade.get_mukti_insight_by_id(
        insight_id,
        tenant_id=scoped,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
    if ins is None:
        raise api_error(code="NOT_FOUND", message="insight not found", status_code=404, request=request)
    return ins
