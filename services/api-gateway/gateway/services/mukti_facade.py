"""Compose feedback records + execution projections; delegate insight computation to mukti-agent."""

from __future__ import annotations

from uuid import UUID

from gateway._bootstrap import ensure_platform_paths

ensure_platform_paths()

from common_schemas import (
    CrossExecutionInsight,
    ExecutionStatus,
    ExecutionSummary,
    MuktiCrossExecutionInput,
    MuktiInsightsSummary,
)
from feedback_service.service import FeedbackService
from mukti_agent.service import MuktiService

from app.services.execution_service import ExecutionService


class MuktiFacade:
    """Does not compute insights in the gateway; loads records and calls MuktiService only."""

    def __init__(
        self,
        *,
        mukti_service: MuktiService,
        feedback_service: FeedbackService,
        execution_service: ExecutionService,
    ) -> None:
        self._mukti = mukti_service
        self._feedback = feedback_service
        self._executions = execution_service

    def get_mukti_insights(
        self,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> MuktiInsightsSummary:
        st: ExecutionStatus | str | None = status
        if status is not None:
            try:
                st = ExecutionStatus(status)
            except ValueError:
                st = status

        executions = self._executions.list_executions(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=st,
            limit=limit,
        )
        scope_ids = {e.execution_id for e in executions}
        summaries = [
            ExecutionSummary(
                execution_id=e.execution_id,
                workflow_type=e.workflow_type,
                status=e.status,
                execution_mode=e.execution_mode,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in executions
        ]

        feedback_pool = self._feedback.list_execution_feedback(limit=min(500, max(limit * 5, limit)))
        feedback = [fb for fb in feedback_pool if fb.execution_id in scope_ids]

        inp = MuktiCrossExecutionInput(
            execution_feedback=feedback,
            execution_summaries=summaries,
        )
        return self._mukti.analyze_cross_execution(inp)

    def get_mukti_insight_by_id(
        self,
        insight_id: UUID,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> CrossExecutionInsight | None:
        summary = self.get_mukti_insights(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=status,
            limit=limit,
        )
        for ins in summary.insights:
            if ins.insight_id == insight_id:
                return ins
        return None
