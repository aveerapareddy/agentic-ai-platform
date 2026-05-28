from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_type: str
    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any]
    idempotency_key: str | None = None


class SubmitApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_proposal_id: UUID | None = None
    policy_evaluation_id: UUID | None = None
    decision: str
    approver: str
    notes: str | None = None


class SubmitFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = "operator_console"
    labels: list[str] | None = None
    detail: dict[str, Any] | None = None
    source_scope: dict[str, Any] | None = None


class ReplayExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "exact"
    plan_id: UUID | None = None
    environment_target: str = "sandbox"
    label: str | None = None
    reason: str | None = None
    requested_by: str | None = None
    input_overrides: dict[str, Any] | None = None
    start_execution: bool = False
