"""EvaluationService: metrics for one execution and aggregates over filtered lists."""

from __future__ import annotations

from uuid import UUID

from evaluation_engine.aggregate import build_full_aggregated_metrics
from evaluation_engine.anomalies import detect_anomalies
from evaluation_engine.metrics import compute_execution_metrics, load_tool_calls_for_execution
from evaluation_engine.models import AggregatedMetrics, EvaluationSummary, ExecutionMetrics
from evaluation_engine.port import AggregatedMetricFilters, ExecutionDataPort
from evaluation_engine.scoring import compute_evaluation_score


class EvaluationService:
    """Computes trace-grounded metrics; read-only against ExecutionDataPort."""

    def __init__(self, store: ExecutionDataPort) -> None:
        self._store = store

    def get_execution_metrics(self, execution_id: UUID) -> ExecutionMetrics | None:
        ex = self._store.get_execution(execution_id)
        if ex is None:
            return None
        tenant_id: str | None = None
        ctx = self._store.get_context(ex.execution_context_id)
        if ctx is not None and hasattr(ctx, "tenant_id"):
            tenant_id = getattr(ctx, "tenant_id", None)

        steps = self._store.list_steps_for_execution(execution_id)
        step_results: dict = {}
        for s in steps:
            sr = self._store.get_step_result(s.step_id)
            if sr is not None:
                step_results[s.step_id] = sr

        tools = load_tool_calls_for_execution(steps, self._store.list_tool_calls_for_step)
        pol = self._store.list_policy_evaluations_for_execution(execution_id)

        return compute_execution_metrics(
            ex,
            steps=steps,
            step_results=step_results,
            tool_calls=tools,
            policy_evaluations=pol,
            tenant_id=tenant_id,
        )

    def get_aggregated_metrics(self, filters: AggregatedMetricFilters) -> AggregatedMetrics:
        executions = self._store.list_executions(
            tenant_id=filters.tenant_id,
            workflow_type=filters.workflow_type,
            status=filters.status,
            limit=filters.limit,
        )
        per: list[ExecutionMetrics] = []
        for ex in executions:
            m = self.get_execution_metrics(ex.execution_id)
            if m is not None:
                per.append(m)

        def load_steps(eid: UUID):
            return self._store.list_steps_for_execution(eid)

        def load_tools(steps):
            return load_tool_calls_for_execution(steps, self._store.list_tool_calls_for_step)

        return build_full_aggregated_metrics(per, executions, load_steps, load_tools)

    def get_evaluation_summary(self, filters: AggregatedMetricFilters) -> EvaluationSummary:
        aggregated = self.get_aggregated_metrics(filters)
        executions = self._store.list_executions(
            tenant_id=filters.tenant_id,
            workflow_type=filters.workflow_type,
            status=filters.status,
            limit=filters.limit,
        )
        per: list[ExecutionMetrics] = []
        for ex in executions:
            m = self.get_execution_metrics(ex.execution_id)
            if m is not None:
                per.append(m)

        anomalies = detect_anomalies(per, aggregated)
        score, score_notes = compute_evaluation_score(aggregated, per)

        scope = (
            f"tenant_id={filters.tenant_id!r}, workflow_type={filters.workflow_type!r}, "
            f"status={filters.status!r}, limit={filters.limit}"
        )
        return EvaluationSummary(
            scope_description=scope,
            execution_sample_size=len(per),
            aggregated=aggregated,
            anomalies=anomalies,
            evaluation_score=score,
            score_formula_notes=score_notes,
        )
