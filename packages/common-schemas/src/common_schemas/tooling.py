"""Tool registration semantics and tool call audit records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel

from .ids import ActionId, ContextId, ExecutionId, StepId, ToolCallId


class ToolSideEffectClass(StrEnum):
    READ_ONLY = "read_only"
    STATE_CHANGING = "state_changing"


class ToolIdempotency(StrEnum):
    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"


class ToolCallStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    REJECTED_BY_POLICY = "rejected_by_policy"


class ToolCallInput(RootModel[dict[str, Any]]):
    """Arguments after schema validation at the tool boundary; shape is tool-specific."""


class ToolCallOutput(RootModel[dict[str, Any]]):
    """Tool result or redacted summary when sensitive."""


class ToolCall(BaseModel):
    """Single audited invocation; emitted to trace and tied to step and execution."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallId
    execution_id: ExecutionId
    step_id: StepId
    execution_context_id: ContextId
    action_proposal_id: ActionId | None = None
    tool_name: str
    side_effect_class: ToolSideEffectClass
    idempotency: ToolIdempotency
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Use ToolCallInput RootModel when validating standalone payloads.",
    )
    output: dict[str, Any] | None = Field(
        default=None,
        description="Use ToolCallOutput RootModel when validating standalone payloads.",
    )
    status: ToolCallStatus
    latency_ms: int | None = Field(default=None, ge=0)
    error: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
