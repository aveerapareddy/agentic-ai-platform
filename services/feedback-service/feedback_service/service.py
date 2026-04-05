"""Ingest operator feedback; persist Mukti execution_feedback (no execution control)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from common_schemas import (
    ExecutionFeedback,
    ExecutionId,
    FeedbackSource,
    OperatorFeedback,
)

from feedback_service.repository import FeedbackRepository, InMemoryFeedbackRepository


class FeedbackService:
    """Owns feedback persistence; does not call orchestrator lifecycle APIs."""

    def __init__(self, repository: FeedbackRepository | None = None) -> None:
        self._repo = repository or InMemoryFeedbackRepository()

    def submit_operator_feedback(
        self,
        *,
        execution_id: ExecutionId,
        source: FeedbackSource,
        labels: list[str] | None = None,
        detail: dict[str, Any] | None = None,
        source_scope: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> OperatorFeedback:
        ts = now or datetime.now(timezone.utc)
        record = OperatorFeedback(
            feedback_record_id=uuid4(),
            execution_id=execution_id,
            source=source,
            labels=list(labels or []),
            detail=dict(detail or {}),
            source_scope=dict(source_scope) if source_scope is not None else None,
            created_at=ts,
            updated_at=None,
        )
        self._repo.save_operator_feedback(record)
        return record

    def list_operator_feedback_for_execution(self, execution_id: ExecutionId) -> list[OperatorFeedback]:
        return self._repo.list_operator_feedback_for_execution(execution_id)

    def save_execution_feedback(self, record: ExecutionFeedback) -> None:
        """Persist Mukti advisory row; callers must not use this to mutate live executions."""
        self._repo.save_execution_feedback(record)

    def list_execution_feedback_for_execution(self, execution_id: ExecutionId) -> list[ExecutionFeedback]:
        return self._repo.list_execution_feedback_for_execution(execution_id)
