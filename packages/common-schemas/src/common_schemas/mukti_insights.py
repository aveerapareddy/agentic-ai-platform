"""Mukti v2 cross-execution insight contracts (advisory only; no control-plane authority)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .execution import ExecutionSummary
from .feedback import ExecutionFeedback
from .ids import ExecutionId, FeedbackId


class InsightSeverity(StrEnum):
    """Operator attention level; derived from explicit evidence thresholds only."""

    INFO = "info"
    WARNING = "warning"
    ELEVATED = "elevated"


class InsightCategory(StrEnum):
    """Bounded insight taxonomy for cross-execution Mukti output."""

    TOP_FAILURE_TYPE = "top_failure_type"
    RECURRING_PATTERN = "recurring_pattern"
    POLICY_FRICTION = "policy_friction"
    MODEL_FALLBACK = "model_fallback"
    UNSTABLE_WORKFLOW = "unstable_workflow"
    UNSTABLE_STEP = "unstable_step"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"


class CrossExecutionInsight(BaseModel):
    """One explainable cross-execution signal; does not mutate live execution state."""

    model_config = ConfigDict(extra="forbid")

    insight_id: UUID
    category: InsightCategory
    severity: InsightSeverity
    title: str = Field(max_length=256)
    description: str = Field(max_length=2048)
    evidence_count: int = Field(ge=0)
    affected_workflows: list[str] = Field(default_factory=list, max_length=32)
    affected_steps: list[str] = Field(default_factory=list, max_length=64)
    suggested_action: str | None = Field(default=None, max_length=1024)
    related_execution_ids: list[ExecutionId] = Field(default_factory=list, max_length=200)
    rank_score: int = Field(
        ge=0,
        description="Deterministic sort key (higher = more prominent); not a hidden model score.",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured tallies or sample keys supporting the insight.",
    )


class RankedImprovementSuggestion(BaseModel):
    """Aggregated advisory suggestion ranked across executions."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    category: str = Field(max_length=128)
    summary: str = Field(max_length=512)
    evidence_count: int = Field(ge=1)
    affected_workflows: list[str] = Field(default_factory=list, max_length=32)
    related_execution_ids: list[ExecutionId] = Field(default_factory=list, max_length=200)
    suggested_action: str | None = Field(default=None, max_length=1024)
    detail: dict[str, Any] = Field(default_factory=dict)


class MuktiInsightsSummary(BaseModel):
    """Cross-execution Mukti v2 rollup for operator surfaces."""

    model_config = ConfigDict(extra="forbid")

    scope_description: str
    execution_feedback_sample_size: int = Field(ge=0)
    top_failure_types: list[CrossExecutionInsight] = Field(default_factory=list)
    recurring_patterns: list[CrossExecutionInsight] = Field(default_factory=list)
    policy_friction_areas: list[CrossExecutionInsight] = Field(default_factory=list)
    model_fallback_concentration: list[CrossExecutionInsight] = Field(default_factory=list)
    unstable_workflows_or_steps: list[CrossExecutionInsight] = Field(default_factory=list)
    ranked_improvement_suggestions: list[RankedImprovementSuggestion] = Field(default_factory=list)
    insights: list[CrossExecutionInsight] = Field(
        default_factory=list,
        description="Flat index of all insights in this summary (for GET by insight_id).",
    )


class MuktiCrossExecutionInput(BaseModel):
    """Frozen inputs for cross-execution analysis; no live orchestrator handles."""

    model_config = ConfigDict(extra="forbid")

    execution_feedback: list[ExecutionFeedback] = Field(default_factory=list)
    execution_summaries: list[ExecutionSummary] = Field(default_factory=list)


class MuktiInsightRef(BaseModel):
    """Lightweight pointer from execution_feedback to related insight ids (optional future use)."""

    model_config = ConfigDict(extra="forbid")

    feedback_id: FeedbackId
    execution_id: ExecutionId
    insight_ids: list[UUID] = Field(default_factory=list)
