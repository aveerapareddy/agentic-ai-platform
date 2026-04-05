"""ORM rows aligned with 001_initial_schema + 002_operator_feedback."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OperatorFeedbackRow(Base):
    __tablename__ = "operator_feedback"

    feedback_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    source_scope: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionFeedbackRow(Base):
    __tablename__ = "execution_feedback"

    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_scope: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_types: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    patterns_detected: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    improvement_suggestions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    advisory_confidence: Mapped[Any | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
