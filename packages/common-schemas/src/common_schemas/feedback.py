"""Operator feedback and post-execution Execution Feedback (Mukti), advisory only."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ExecutionId, FeedbackId


class FeedbackSource(StrEnum):
    """Origin of operator- or integration-submitted feedback."""

    OPERATOR_CONSOLE = "operator_console"
    INTEGRATION = "integration"
    API = "api"


class OperatorFeedback(BaseModel):
    """Human or pipeline feedback tied to an execution; does not mutate live execution."""

    model_config = ConfigDict(extra="forbid")

    feedback_record_id: FeedbackId
    execution_id: ExecutionId
    source: FeedbackSource
    labels: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)
    source_scope: dict[str, Any] | None = Field(
        default=None,
        description="Optional batch or aggregation scope metadata.",
    )
    created_at: datetime
    updated_at: datetime | None = Field(
        default=None,
        description="Set when records are corrected or reconciled; immutable-first otherwise.",
    )


class PatternDetection(BaseModel):
    """Structured pattern noted in post-execution analysis."""

    model_config = ConfigDict(extra="forbid")

    pattern_type: str
    description: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ImprovementSuggestion(BaseModel):
    """Advisory recommendation; requires governed change process before production effect."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(description="e.g. policy_rule, validator, tool_contract, prompt.")
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ExecutionFeedback(BaseModel):
    """Mukti post-execution analysis record; not a control-plane message."""

    model_config = ConfigDict(extra="forbid")

    feedback_id: FeedbackId
    execution_id: ExecutionId
    source_scope: dict[str, Any] | None = None
    failure_types: list[str] = Field(default_factory=list)
    patterns_detected: list[PatternDetection] = Field(default_factory=list)
    improvement_suggestions: list[ImprovementSuggestion] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = Field(
        default=None,
        description="Optional; use when advisory rows are amended after initial write.",
    )
