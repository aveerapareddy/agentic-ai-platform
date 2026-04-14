"""Thin adapter: map HTTP query params to evaluation_engine; no metric formulas here."""

from __future__ import annotations

from uuid import UUID

from gateway._bootstrap import ensure_platform_paths

ensure_platform_paths()

from gateway.schemas.evaluation import (
    AggregatedMetricsResponse,
    AnomaliesInsightResponse,
    AnomalyFindingResponse,
    ExecutionMetricsResponse,
    aggregated_metrics_to_response,
    execution_metrics_to_response,
)
from common_schemas import ExecutionStatus
from evaluation_engine import AggregatedMetricFilters, EvaluationService


class EvaluationFacade:
    """Forwards reads to EvaluationService only."""

    def __init__(self, *, evaluation_service: EvaluationService) -> None:
        self._svc = evaluation_service

    def _filters(
        self,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> AggregatedMetricFilters:
        st: ExecutionStatus | str | None = status
        if status is not None:
            try:
                st = ExecutionStatus(status)
            except ValueError:
                st = status
        return AggregatedMetricFilters(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=st,
            limit=limit,
        )

    def get_execution_metrics(self, execution_id: UUID) -> ExecutionMetricsResponse | None:
        m = self._svc.get_execution_metrics(execution_id)
        if m is None:
            return None
        return execution_metrics_to_response(m)

    def get_aggregated_metrics(
        self,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> AggregatedMetricsResponse:
        f = self._filters(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=status,
            limit=limit,
        )
        return aggregated_metrics_to_response(self._svc.get_aggregated_metrics(f))

    def get_anomalies_insight(
        self,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> AnomaliesInsightResponse:
        f = self._filters(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=status,
            limit=limit,
        )
        summary = self._svc.get_evaluation_summary(f)
        return AnomaliesInsightResponse(
            scope_description=summary.scope_description,
            execution_sample_size=summary.execution_sample_size,
            anomalies=[AnomalyFindingResponse.model_validate(a.model_dump(mode="json")) for a in summary.anomalies],
        )
