"""Execution lifecycle, context, and replay-oriented shared types."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ContextId, ExecutionId, PlanId


class ExecutionStatus(StrEnum):
    """Coarse execution lifecycle; terminal states do not transition further."""

    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(StrEnum):
    """How the run is driven: operator-tight loop vs asynchronous platform execution."""

    INTERACTIVE = "interactive"
    BACKGROUND = "background"


class ExecutionContext(BaseModel):
    """First-class tenant, principal, environment, and policy scope for a run."""

    model_config = ConfigDict(extra="forbid")

    context_id: ContextId
    tenant_id: str
    principal_id: str | None = None
    actor: str | None = None
    request_id: str
    environment: str
    permissions_scope: dict[str, Any] = Field(default_factory=dict)
    policy_scope: str
    feature_flags: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class Execution(BaseModel):
    """Durable unit of work from accepted input through a terminal state."""

    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    workflow_type: str
    status: ExecutionStatus
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.BACKGROUND,
        description="Interactive runs correlate with operator-driven pacing; background for async workflows.",
    )
    execution_context_id: ContextId
    parent_execution_id: ExecutionId | None = None
    current_plan_id: PlanId | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    trace_timeline: list[dict[str, Any]] = Field(default_factory=list)
    validation_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


class ExecutionSummary(BaseModel):
    """Projected execution for list and poll responses."""

    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    workflow_type: str
    status: ExecutionStatus
    execution_mode: ExecutionMode | None = Field(
        default=None,
        description="Omitted in legacy projections until backfilled.",
    )
    created_at: datetime
    updated_at: datetime


class ExecutionTraceReference(BaseModel):
    """Pointer to trace materialization for an execution (API or internal)."""

    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    trace_uri: str | None = Field(
        default=None,
        description="Optional stable URI or path template for GET trace aggregate.",
    )
    trace_summary: dict[str, Any] | None = Field(
        default=None,
        description="Lightweight counts or redacted rollup for list/hub views without full trace payload.",
    )


class ReplayMode(StrEnum):
    """Exact vs investigative replay per runtime model."""

    EXACT = "exact"
    INVESTIGATIVE = "investigative"


class ReplayRequest(BaseModel):
    """Request to start a replay run anchored on a source execution."""

    model_config = ConfigDict(extra="forbid")

    source_execution_id: ExecutionId = Field(
        description="Execution whose trace and inputs anchor the replay.",
    )
    replay_mode: ReplayMode = Field(
        description="Exact replay reproduces structure; investigative allows sandbox overrides.",
    )
    environment_target: str = Field(
        description="Deployment slice for replay (e.g. sandbox).",
    )
    anchor_plan_id: PlanId | None = Field(
        default=None,
        description="Plan revision to use; defaults to stored current or latest per platform rules.",
    )
    override_plan: dict[str, Any] | None = Field(
        default=None,
        description="Investigative-only plan fragment or hints; ignored or rejected for exact mode per policy.",
    )
    reason: str | None = Field(default=None, description="Audit justification for replay.")
    requested_by: str | None = Field(
        default=None,
        description="Principal or service identity requesting replay.",
    )
    execution_mode: ExecutionMode | None = Field(
        default=None,
        description="Scheduling hint for the replay execution; platform default if omitted.",
    )
    label: str | None = Field(default=None, description="Operator or audit label for the replay run.")
