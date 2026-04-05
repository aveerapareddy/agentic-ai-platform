"""Persistence for operator_feedback and execution_feedback (Mukti) rows."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from common_schemas import (
    ExecutionFeedback,
    FeedbackSource,
    ImprovementSuggestion,
    OperatorFeedback,
    PatternDetection,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from feedback_service.models import ExecutionFeedbackRow, OperatorFeedbackRow


class FeedbackRepository(Protocol):
    def save_operator_feedback(self, record: OperatorFeedback) -> None: ...
    def get_operator_feedback(self, feedback_record_id: UUID) -> OperatorFeedback | None: ...
    def list_operator_feedback_for_execution(self, execution_id: UUID) -> list[OperatorFeedback]: ...

    def save_execution_feedback(self, record: ExecutionFeedback) -> None: ...
    def get_execution_feedback(self, feedback_id: UUID) -> ExecutionFeedback | None: ...
    def list_execution_feedback_for_execution(self, execution_id: UUID) -> list[ExecutionFeedback]: ...


class InMemoryFeedbackRepository:
    def __init__(self) -> None:
        self._operator: dict[UUID, OperatorFeedback] = {}
        self._mukti: dict[UUID, ExecutionFeedback] = {}

    def save_operator_feedback(self, record: OperatorFeedback) -> None:
        self._operator[record.feedback_record_id] = record

    def get_operator_feedback(self, feedback_record_id: UUID) -> OperatorFeedback | None:
        return self._operator.get(feedback_record_id)

    def list_operator_feedback_for_execution(self, execution_id: UUID) -> list[OperatorFeedback]:
        return sorted(
            (r for r in self._operator.values() if r.execution_id == execution_id),
            key=lambda r: r.created_at,
        )

    def save_execution_feedback(self, record: ExecutionFeedback) -> None:
        self._mukti[record.feedback_id] = record

    def get_execution_feedback(self, feedback_id: UUID) -> ExecutionFeedback | None:
        return self._mukti.get(feedback_id)

    def list_execution_feedback_for_execution(self, execution_id: UUID) -> list[ExecutionFeedback]:
        return sorted(
            (r for r in self._mukti.values() if r.execution_id == execution_id),
            key=lambda r: r.created_at,
        )


def _op_to_row(r: OperatorFeedback) -> OperatorFeedbackRow:
    return OperatorFeedbackRow(
        feedback_record_id=r.feedback_record_id,
        execution_id=r.execution_id,
        source=r.source.value,
        labels=list(r.labels),
        detail=dict(r.detail),
        source_scope=dict(r.source_scope) if r.source_scope is not None else None,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _row_to_op(row: OperatorFeedbackRow) -> OperatorFeedback:
    return OperatorFeedback(
        feedback_record_id=row.feedback_record_id,
        execution_id=row.execution_id,
        source=FeedbackSource(row.source),
        labels=list(row.labels or []),
        detail=dict(row.detail or {}),
        source_scope=dict(row.source_scope) if row.source_scope is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _confidence_to_python(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _ef_to_row(r: ExecutionFeedback) -> ExecutionFeedbackRow:
    return ExecutionFeedbackRow(
        feedback_id=r.feedback_id,
        execution_id=r.execution_id,
        source_scope=dict(r.source_scope) if r.source_scope is not None else None,
        failure_types=list(r.failure_types),
        patterns_detected=[p.model_dump(mode="json") for p in r.patterns_detected],
        improvement_suggestions=[s.model_dump(mode="json") for s in r.improvement_suggestions],
        advisory_confidence=r.advisory_confidence,
        created_at=r.created_at,
    )


def _row_to_ef(row: ExecutionFeedbackRow) -> ExecutionFeedback:
    pats = [PatternDetection.model_validate(x) for x in (row.patterns_detected or [])]
    sugs = [ImprovementSuggestion.model_validate(x) for x in (row.improvement_suggestions or [])]
    return ExecutionFeedback(
        feedback_id=row.feedback_id,
        execution_id=row.execution_id,
        source_scope=dict(row.source_scope) if row.source_scope is not None else None,
        failure_types=list(row.failure_types or []),
        patterns_detected=pats,
        improvement_suggestions=sugs,
        advisory_confidence=_confidence_to_python(row.advisory_confidence),
        created_at=row.created_at,
        updated_at=None,
    )


class PostgresFeedbackRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_operator_feedback(self, record: OperatorFeedback) -> None:
        with self._session_factory() as session:
            session.merge(_op_to_row(record))
            session.commit()

    def get_operator_feedback(self, feedback_record_id: UUID) -> OperatorFeedback | None:
        with self._session_factory() as session:
            row = session.get(OperatorFeedbackRow, feedback_record_id)
            return _row_to_op(row) if row is not None else None

    def list_operator_feedback_for_execution(self, execution_id: UUID) -> list[OperatorFeedback]:
        with self._session_factory() as session:
            stmt = (
                select(OperatorFeedbackRow)
                .where(OperatorFeedbackRow.execution_id == execution_id)
                .order_by(OperatorFeedbackRow.created_at.asc())
            )
            rows = session.scalars(stmt).all()
            return [_row_to_op(r) for r in rows]

    def save_execution_feedback(self, record: ExecutionFeedback) -> None:
        with self._session_factory() as session:
            session.merge(_ef_to_row(record))
            session.commit()

    def get_execution_feedback(self, feedback_id: UUID) -> ExecutionFeedback | None:
        with self._session_factory() as session:
            row = session.get(ExecutionFeedbackRow, feedback_id)
            return _row_to_ef(row) if row is not None else None

    def list_execution_feedback_for_execution(self, execution_id: UUID) -> list[ExecutionFeedback]:
        with self._session_factory() as session:
            stmt = (
                select(ExecutionFeedbackRow)
                .where(ExecutionFeedbackRow.execution_id == execution_id)
                .order_by(ExecutionFeedbackRow.created_at.asc())
            )
            rows = session.scalars(stmt).all()
            return [_row_to_ef(r) for r in rows]
