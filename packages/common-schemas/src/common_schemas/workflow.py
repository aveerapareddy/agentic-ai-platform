"""Execution plans, steps, step results, and validation outcomes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ExecutionId, PlanId, ResultId, StepId


class StepStatus(StrEnum):
    """Step-level lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StepType(StrEnum):
    """Common step categories; workflow-specific kinds remain valid as plain strings."""

    RETRIEVAL = "retrieval"
    TOOL = "tool"
    REASONING = "reasoning"
    VALIDATION = "validation"
    ACTION = "action"


class StepCompleteness(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    DEGRADED = "degraded"


class StepDependency(BaseModel):
    """Reference to an upstream step in the plan graph."""

    model_config = ConfigDict(extra="forbid")

    step_id: StepId


class ExecutionPlan(BaseModel):
    """Versioned, inspectable plan revision; re-plan appends lineage."""

    model_config = ConfigDict(extra="forbid")

    plan_id: PlanId
    execution_id: ExecutionId
    parent_plan_id: PlanId | None = None
    plan_version: int = Field(ge=1)
    revision_reason: str | None = None
    goal: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Abstract step specifications from planner (types, bindings, templates).",
    )
    dependencies: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Directed edges or refs defining partial order.",
    )
    ordering: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Step(BaseModel):
    """Unit of work scheduled by the orchestrator."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    step_id: StepId
    execution_id: ExecutionId
    plan_id: PlanId
    step_type: StepType | str = Field(
        validation_alias="type",
        serialization_alias="type",
        description="Planner step kind; matches DB/API `type`; extensible beyond StepType enum.",
    )
    agent: str
    input: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus
    dependencies: list[StepDependency] = Field(default_factory=list)
    retry_count: int = Field(default=0, ge=0)
    degraded_allowed: bool = False
    created_at: datetime
    updated_at: datetime


class ValidationOutcome(BaseModel):
    """Validator output; overrides advisory confidence on promotion paths."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="e.g. passed, failed, skipped, inconclusive.")
    details: dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Primary output and evidence for a step; 1:1 with Step."""

    model_config = ConfigDict(extra="forbid")

    step_result_id: ResultId
    step_id: StepId
    output: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int | None = Field(default=None, ge=0)
    latency_started_at: datetime | None = None
    latency_ended_at: datetime | None = None
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Advisory scalar; validation outcomes govern correctness.",
    )
    confidence_detail: dict[str, Any] | None = Field(
        default=None,
        description="Non-scalar calibration metadata (model id, rationale, etc.).",
    )
    completeness: StepCompleteness | None = None
    validation_outcome: ValidationOutcome | None = None
    created_at: datetime
    updated_at: datetime
