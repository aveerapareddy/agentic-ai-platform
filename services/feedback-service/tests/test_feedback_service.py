"""Operator feedback ingestion and execution_feedback persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import ExecutionFeedback, FeedbackSource

from feedback_service.repository import InMemoryFeedbackRepository
from feedback_service.service import FeedbackService


def test_submit_operator_feedback_shape() -> None:
    svc = FeedbackService()
    eid = uuid4()
    rec = svc.submit_operator_feedback(
        execution_id=eid,
        source=FeedbackSource.OPERATOR_CONSOLE,
        labels=["severity_mismatch"],
        detail={"note": "operator review"},
    )
    assert rec.feedback_record_id
    assert rec.execution_id == eid
    assert rec.source == FeedbackSource.OPERATOR_CONSOLE
    assert "severity_mismatch" in rec.labels
    assert rec.detail.get("note") == "operator review"
    listed = svc.list_operator_feedback_for_execution(eid)
    assert len(listed) == 1
    assert listed[0].feedback_record_id == rec.feedback_record_id


def test_save_execution_feedback_roundtrip() -> None:
    repo = InMemoryFeedbackRepository()
    svc = FeedbackService(repository=repo)
    eid = uuid4()
    now = datetime.now(timezone.utc)
    ef = ExecutionFeedback(
        feedback_id=uuid4(),
        execution_id=eid,
        failure_types=["test_signal"],
        patterns_detected=[],
        improvement_suggestions=[],
        advisory_confidence=0.9,
        created_at=now,
    )
    svc.save_execution_feedback(ef)
    got = svc.list_execution_feedback_for_execution(eid)
    assert len(got) == 1
    assert got[0].failure_types == ["test_signal"]
    assert got[0].advisory_confidence == pytest.approx(0.9)
