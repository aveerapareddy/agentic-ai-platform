"""Gateway response models for evaluation metrics — field sets mirror evaluation_engine (trace-grounded)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from evaluation_engine.models import (
    AggregatedMetrics,
    AnomalyFinding,
    ExecutionMetrics,
)


class ExecutionMetricsResponse(ExecutionMetrics):
    """Per-execution metrics; computed only inside evaluation-engine."""


class AggregatedMetricsResponse(AggregatedMetrics):
    """Cross-execution rollups; computed only inside evaluation-engine."""


class AnomalyFindingResponse(AnomalyFinding):
    """Rule-based anomaly row (code, severity, explanation, evidence)."""


class AnomaliesInsightResponse(BaseModel):
    """Subset of evaluation summary for operators focused on anomaly signals."""

    model_config = ConfigDict(extra="forbid")

    scope_description: str
    execution_sample_size: int = Field(ge=0)
    anomalies: list[AnomalyFindingResponse] = Field(default_factory=list)


def execution_metrics_to_response(m: ExecutionMetrics) -> ExecutionMetricsResponse:
    return ExecutionMetricsResponse.model_validate(m.model_dump(mode="json"))


def aggregated_metrics_to_response(m: AggregatedMetrics) -> AggregatedMetricsResponse:
    return AggregatedMetricsResponse.model_validate(m.model_dump(mode="json"))
