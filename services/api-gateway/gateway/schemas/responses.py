from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorEnvelope


class CreateExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    status: str
    workflow_type: str
    created_at: datetime
    links: dict[str, str] = Field(default_factory=dict)


class ExecutionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    workflow_type: str
    status: str
    execution_context_id: UUID
    current_plan_id: UUID | None
    parent_execution_id: UUID | None
    input: dict[str, Any]
    result: dict[str, Any] | None
    validation_summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None


class ExecutionListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    status: str
    workflow_type: str
    created_at: datetime


class ListExecutionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExecutionListItem]
    next_cursor: str | None = None


class TraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str
    execution_context: dict[str, Any]
    plans: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    policy_evaluations: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    timeline: list[dict[str, Any]]


class ApprovalCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: UUID
    execution_id: UUID
    decision: str
    decided_at: datetime


class FeedbackCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_record_id: UUID
    execution_id: UUID
    created_at: datetime


# ReplayCreatedResponse from common_schemas is the canonical replay response shape.
