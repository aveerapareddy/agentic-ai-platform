from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from gateway.dependencies import EvaluationFacadeDep
from gateway.http_errors import api_error
from gateway.schemas.evaluation import AggregatedMetricsResponse, AnomaliesInsightResponse, ExecutionMetricsResponse

router = APIRouter(tags=["metrics"])


@router.get("/executions/{execution_id}/metrics", response_model=ExecutionMetricsResponse)
def get_execution_metrics(
    execution_id: UUID,
    request: Request,
    facade: EvaluationFacadeDep,
) -> ExecutionMetricsResponse:
    m = facade.get_execution_metrics(execution_id)
    if m is None:
        raise api_error(code="NOT_FOUND", message="execution not found", status_code=404, request=request)
    return m


@router.get("/metrics", response_model=AggregatedMetricsResponse)
def get_aggregated_metrics(
    facade: EvaluationFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> AggregatedMetricsResponse:
    return facade.get_aggregated_metrics(
        tenant_id=tenant_id,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )


@router.get("/insights/anomalies", response_model=AnomaliesInsightResponse)
def get_anomalies_insight(
    facade: EvaluationFacadeDep,
    tenant_id: str | None = Query(default=None),
    workflow_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> AnomaliesInsightResponse:
    return facade.get_anomalies_insight(
        tenant_id=tenant_id,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
