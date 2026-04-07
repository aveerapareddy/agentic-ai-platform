"""Delegate operator feedback to feedback-service only."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from gateway._bootstrap import ensure_platform_paths

ensure_platform_paths()

from common_schemas import FeedbackSource, OperatorFeedback
from feedback_service.service import FeedbackService


class FeedbackFacade:
    def __init__(self, *, feedback_service: FeedbackService) -> None:
        self._svc = feedback_service

    def submit_feedback(
        self,
        execution_id: UUID,
        *,
        source: str,
        labels: list[str] | None,
        detail: dict[str, Any] | None,
        source_scope: dict[str, Any] | None,
    ) -> OperatorFeedback:
        try:
            fs = FeedbackSource(source)
        except ValueError as e:
            raise ValueError(f"invalid feedback source: {source}") from e
        return self._svc.submit_operator_feedback(
            execution_id=execution_id,
            source=fs,
            labels=labels,
            detail=detail,
            source_scope=source_scope,
        )
