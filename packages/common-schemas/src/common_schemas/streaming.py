"""SSE execution stream event contracts (Session F — observational only)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ExecutionId


class ExecutionStreamEventType(StrEnum):
    EXECUTION_UPDATED = "execution_updated"
    STEP_UPDATED = "step_updated"
    TRACE_EVENT = "trace_event"
    APPROVAL_REQUIRED = "approval_required"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    REPLAY_CREATED = "replay_created"
    HEARTBEAT = "heartbeat"


_TERMINAL_STREAM_EVENTS = frozenset(
    {
        ExecutionStreamEventType.EXECUTION_COMPLETED,
        ExecutionStreamEventType.EXECUTION_FAILED,
        ExecutionStreamEventType.EXECUTION_CANCELLED,
    },
)


class ExecutionStreamEvent(BaseModel):
    """Bounded server→client observation; orchestrator/repository remain source of truth."""

    model_config = ConfigDict(extra="forbid")

    event_type: ExecutionStreamEventType
    execution_id: ExecutionId
    sequence: int = Field(ge=0)
    emitted_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.event_type in _TERMINAL_STREAM_EVENTS
