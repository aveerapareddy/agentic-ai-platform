"""Structured replay comparison output (read-only, deterministic)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .execution import ReplayMode
from .ids import ExecutionId, StepId, ToolCallId


class ReplayDiffSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    SIGNIFICANT = "significant"


class ReplayDiffCategory(StrEnum):
    LINEAGE = "lineage"
    EXECUTION_STATUS = "execution_status"
    INPUT = "input"
    PLAN = "plan"
    STEP = "step"
    MODEL_REASONING = "model_reasoning"
    TOOL_CALL = "tool_call"
    POLICY = "policy"
    VALIDATION = "validation"
    RESULT = "result"


class ReplayDiffItem(BaseModel):
    """One explainable difference between source and replay executions."""

    model_config = ConfigDict(extra="forbid")

    category: ReplayDiffCategory
    severity: ReplayDiffSeverity
    title: str = Field(max_length=256)
    description: str = Field(max_length=2048)
    source_value: str | None = Field(
        default=None,
        max_length=512,
        description="Bounded string rendering of source side for operators.",
    )
    replay_value: str | None = Field(default=None, max_length=512)
    path: str = Field(max_length=256, description="Logical field path, e.g. input.severity or steps[1].status.")
    related_step_id: StepId | None = None
    related_tool_call_id: ToolCallId | None = None


class ReplayDiffSummary(BaseModel):
    """Full comparison of a replay child against its source execution."""

    model_config = ConfigDict(extra="forbid")

    source_execution_id: ExecutionId
    replay_execution_id: ExecutionId
    replay_mode: ReplayMode | None = None
    linked_to_source: bool
    total_differences: int = Field(ge=0)
    significant_differences: int = Field(ge=0)
    items: list[ReplayDiffItem] = Field(default_factory=list, max_length=500)
