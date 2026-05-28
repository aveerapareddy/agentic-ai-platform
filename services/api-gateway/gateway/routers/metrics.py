from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from gateway.dependencies import EvaluationFacadeDep, GatewayState, get_state
from fastapi import Depends
from gateway.http_errors import api_error
from gateway.rbac import MetricsReadDep
from gateway.schemas.evaluation import AggregatedMetricsResponse, AnomaliesInsightResponse, ExecutionMetricsResponse
from gateway.tenant_access import assert_execution_visible

router = APIRouter(tags=["metrics"])


def _scoped_tenant_id(request: Request, auth: MetricsReadDep, tenant_id: str | None) -> str:
    scoped = auth.tenant.tenant_id
    if tenant_id is not None and tenant_id != scoped:
        raise api_error(
            code="FORBIDDEN",
            message="tenant_id query must match authenticated tenant",
            status_code=403,
            request=request,
        )
    return scoped


@router.get("/executions/{execution_id}/metrics", response_model=ExecutionMetricsResponse)
def get_execution_metrics(
    execution_id: UUID,
    request: Request,
    auth: MetricsReadDep,
    facade: EvaluationFacadeDep,
    state: GatewayState = Depends(get_state),
) -> ExecutionMetricsResponse:
    assert_execution_visible(state.repository, execution_id, auth, request=request)
    m = facade.get_execution_metrics(execution_id)
    if m is None:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request)
    return m


@router.get("/metrics", response_model=AggregatedMetricsResponse)
def get_aggregated_metrics(
    request: Request,
    auth: MetricsReadDep,
    facade: EvaluationFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> AggregatedMetricsResponse:
    scoped = _scoped_tenant_id(request, auth, tenant_id)
    return facade.get_aggregated_metrics(
        tenant_id=scoped,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )


@router.get("/insights/anomalies", response_model=AnomaliesInsightResponse)
def get_anomalies_insight(
    request: Request,
    auth: MetricsReadDep,
    facade: EvaluationFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> AnomaliesInsightResponse:
    scoped = _scoped_tenant_id(request, auth, tenant_id)
    return facade.get_anomalies_insight(
        tenant_id=scoped,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
