from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from gateway.dependencies import MuktiFacadeDep
from gateway.http_errors import api_error
from gateway.schemas.mukti import CrossExecutionInsightResponse, MuktiInsightsSummaryResponse

router = APIRouter(tags=["insights"])


@router.get("/insights/mukti", response_model=MuktiInsightsSummaryResponse)
def get_mukti_insights(
    facade: MuktiFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> MuktiInsightsSummaryResponse:
    return facade.get_mukti_insights(
        tenant_id=tenant_id,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )


@router.get("/insights/mukti/{insight_id}", response_model=CrossExecutionInsightResponse)
def get_mukti_insight(
    insight_id: UUID,
    request: Request,
    facade: MuktiFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> CrossExecutionInsightResponse:
    ins = facade.get_mukti_insight_by_id(
        insight_id,
        tenant_id=tenant_id,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
    if ins is None:
        raise api_error(code="NOT_FOUND", message="insight not found", status_code=404, request=request)
    return ins
