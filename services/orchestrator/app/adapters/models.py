"""SQLAlchemy rows aligned with infra/db/migrations/001_initial_schema.sql (subset)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExecutionContextRow(Base):
    __tablename__ = "execution_context"

    context_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    principal_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    permissions_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    policy_scope: Mapped[str] = mapped_column(Text, nullable=False)
    feature_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExecutionRow(Base):
    __tablename__ = "executions"

    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    workflow_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    execution_context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_context.context_id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.execution_id", ondelete="SET NULL"),
        nullable=True,
    )
    current_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_plans.plan_id", ondelete="SET NULL"),
        nullable=True,
    )
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    trace_timeline: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionPlanRow(Base):
    __tablename__ = "execution_plans"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_plans.plan_id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    dependencies: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    ordering: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExecutionStepRow(Base):
    __tablename__ = "execution_steps"

    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_plans.plan_id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column("type", Text, nullable=False)
    agent: Mapped[str] = mapped_column(Text, nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    degraded_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StepResultRow(Base):
    __tablename__ = "step_results"

    step_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_steps.step_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    errors: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[Any | None] = mapped_column(Numeric, nullable=True)
    confidence_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    completeness: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
