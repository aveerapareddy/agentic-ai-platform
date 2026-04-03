"""Persistence port: in-memory and PostgreSQL implementations (shared schemas at the boundary)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from common_schemas import (
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionPlan,
    ExecutionStatus,
    Step,
    StepCompleteness,
    StepDependency,
    StepResult,
    StepStatus,
    StepType,
    ValidationOutcome,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.models import (
    ExecutionContextRow,
    ExecutionPlanRow,
    ExecutionRow,
    ExecutionStepRow,
    StepResultRow,
)


class Repository(Protocol):
    """Repository interface: all execution state persists through this port."""

    def save_context(self, context: ExecutionContext) -> None: ...
    def get_context(self, context_id: UUID) -> ExecutionContext | None: ...

    def save_execution(self, execution: Execution) -> None: ...
    def get_execution(self, execution_id: UUID) -> Execution | None: ...
    def update_execution(self, execution: Execution) -> None: ...

    def save_plan(self, plan: ExecutionPlan) -> None: ...
    def get_plan(self, plan_id: UUID) -> ExecutionPlan | None: ...

    def save_step(self, step: Step) -> None: ...
    def get_step(self, step_id: UUID) -> Step | None: ...
    def update_step(self, step: Step) -> None: ...
    def list_steps_for_execution(self, execution_id: UUID) -> list[Step]: ...

    def save_step_result(self, result: StepResult) -> None: ...
    def get_step_result(self, step_id: UUID) -> StepResult | None: ...


class InMemoryRepository:
    """Volatile store; structurally aligned with relational persistence."""

    def __init__(self) -> None:
        self._contexts: dict[UUID, ExecutionContext] = {}
        self._executions: dict[UUID, Execution] = {}
        self._plans: dict[UUID, ExecutionPlan] = {}
        self._steps: dict[UUID, Step] = {}
        self._step_results: dict[UUID, StepResult] = {}

    def save_context(self, context: ExecutionContext) -> None:
        self._contexts[context.context_id] = context

    def get_context(self, context_id: UUID) -> ExecutionContext | None:
        return self._contexts.get(context_id)

    def save_execution(self, execution: Execution) -> None:
        self._executions[execution.execution_id] = execution

    def get_execution(self, execution_id: UUID) -> Execution | None:
        return self._executions.get(execution_id)

    def update_execution(self, execution: Execution) -> None:
        if execution.execution_id not in self._executions:
            msg = f"execution {execution.execution_id} not found"
            raise KeyError(msg)
        self._executions[execution.execution_id] = execution

    def save_plan(self, plan: ExecutionPlan) -> None:
        self._plans[plan.plan_id] = plan

    def get_plan(self, plan_id: UUID) -> ExecutionPlan | None:
        return self._plans.get(plan_id)

    def save_step(self, step: Step) -> None:
        self._steps[step.step_id] = step

    def get_step(self, step_id: UUID) -> Step | None:
        return self._steps.get(step_id)

    def update_step(self, step: Step) -> None:
        if step.step_id not in self._steps:
            msg = f"step {step.step_id} not found"
            raise KeyError(msg)
        self._steps[step.step_id] = step

    def list_steps_for_execution(self, execution_id: UUID) -> list[Step]:
        return sorted(
            (s for s in self._steps.values() if s.execution_id == execution_id),
            key=lambda s: s.created_at,
        )

    def save_step_result(self, result: StepResult) -> None:
        self._step_results[result.step_id] = result

    def get_step_result(self, step_id: UUID) -> StepResult | None:
        return self._step_results.get(step_id)


# 001_initial_schema.sql has no execution_mode column; reserve a JSONB key inside executions.input for round-trip.
# Do not use this key in workflow payloads; a future migration should add a dedicated column and strip this bridge.
_ORCH_EXECUTION_MODE_KEY = "__orch_execution_mode__"


def _step_type_to_str(value: StepType | str) -> str:
    if isinstance(value, StepType):
        return value.value
    return str(value)


def _step_status_from_str(value: str) -> StepStatus:
    return StepStatus(value)


def _execution_status_from_str(value: str) -> ExecutionStatus:
    return ExecutionStatus(value)


def _persist_execution_input(execution: Execution) -> dict[str, Any]:
    body = dict(execution.input)
    body[_ORCH_EXECUTION_MODE_KEY] = execution.execution_mode.value
    return body


def _restore_execution_input_and_mode(data: dict[str, Any]) -> tuple[dict[str, Any], ExecutionMode]:
    raw = dict(data)
    mode_raw = raw.pop(_ORCH_EXECUTION_MODE_KEY, None)
    if mode_raw is None:
        return raw, ExecutionMode.BACKGROUND
    try:
        return raw, ExecutionMode(str(mode_raw))
    except ValueError:
        return raw, ExecutionMode.BACKGROUND


def _dependencies_to_json(deps: list[StepDependency]) -> list[dict[str, Any]]:
    return [{"step_id": str(d.step_id)} for d in deps]


def _dependencies_from_json(raw: Any) -> list[StepDependency]:
    if not raw:
        return []
    out: list[StepDependency] = []
    for item in raw:
        if isinstance(item, dict) and "step_id" in item:
            out.append(StepDependency(step_id=UUID(str(item["step_id"]))))
    return out


def _confidence_to_python(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _context_to_row(ctx: ExecutionContext) -> ExecutionContextRow:
    return ExecutionContextRow(
        context_id=ctx.context_id,
        tenant_id=ctx.tenant_id,
        principal_id=ctx.principal_id,
        actor=ctx.actor,
        request_id=ctx.request_id,
        environment=ctx.environment,
        permissions_scope=dict(ctx.permissions_scope),
        policy_scope=ctx.policy_scope,
        feature_flags=dict(ctx.feature_flags) if ctx.feature_flags is not None else None,
        created_at=ctx.created_at,
        updated_at=ctx.updated_at,
    )


def _row_to_context(row: ExecutionContextRow) -> ExecutionContext:
    return ExecutionContext(
        context_id=row.context_id,
        tenant_id=row.tenant_id,
        principal_id=row.principal_id,
        actor=row.actor,
        request_id=row.request_id,
        environment=row.environment,
        permissions_scope=dict(row.permissions_scope or {}),
        policy_scope=row.policy_scope,
        feature_flags=dict(row.feature_flags) if row.feature_flags is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _execution_to_row(execution: Execution) -> ExecutionRow:
    return ExecutionRow(
        execution_id=execution.execution_id,
        workflow_type=execution.workflow_type,
        status=execution.status.value,
        execution_context_id=execution.execution_context_id,
        parent_execution_id=execution.parent_execution_id,
        current_plan_id=execution.current_plan_id,
        input=_persist_execution_input(execution),
        result=dict(execution.result) if execution.result is not None else None,
        trace_timeline=list(execution.trace_timeline),
        validation_summary=dict(execution.validation_summary) if execution.validation_summary is not None else None,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
        completed_at=execution.completed_at,
        cancelled_at=execution.cancelled_at,
    )


def _row_to_execution(row: ExecutionRow) -> Execution:
    input_clean, mode = _restore_execution_input_and_mode(dict(row.input or {}))
    return Execution(
        execution_id=row.execution_id,
        workflow_type=row.workflow_type,
        status=_execution_status_from_str(row.status),
        execution_mode=mode,
        execution_context_id=row.execution_context_id,
        parent_execution_id=row.parent_execution_id,
        current_plan_id=row.current_plan_id,
        input=input_clean,
        result=dict(row.result) if row.result is not None else None,
        trace_timeline=list(row.trace_timeline or []),
        validation_summary=dict(row.validation_summary) if row.validation_summary is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        cancelled_at=row.cancelled_at,
    )


def _plan_to_row(plan: ExecutionPlan) -> ExecutionPlanRow:
    return ExecutionPlanRow(
        plan_id=plan.plan_id,
        execution_id=plan.execution_id,
        parent_plan_id=plan.parent_plan_id,
        plan_version=plan.plan_version,
        revision_reason=plan.revision_reason,
        goal=dict(plan.goal),
        steps=list(plan.steps),
        dependencies=list(plan.dependencies),
        ordering=dict(plan.ordering),
        metadata_=dict(plan.metadata),
        created_at=plan.created_at,
    )


def _row_to_plan(row: ExecutionPlanRow) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id=row.plan_id,
        execution_id=row.execution_id,
        parent_plan_id=row.parent_plan_id,
        plan_version=row.plan_version,
        revision_reason=row.revision_reason,
        goal=dict(row.goal or {}),
        steps=list(row.steps or []),
        dependencies=list(row.dependencies or []),
        ordering=dict(row.ordering or {}),
        metadata=dict(row.metadata_ or {}),
        created_at=row.created_at,
    )


def _step_to_row(step: Step) -> ExecutionStepRow:
    return ExecutionStepRow(
        step_id=step.step_id,
        execution_id=step.execution_id,
        plan_id=step.plan_id,
        type=_step_type_to_str(step.step_type),
        agent=step.agent,
        input=dict(step.input),
        status=step.status.value,
        dependencies=_dependencies_to_json(step.dependencies),
        retry_count=step.retry_count,
        degraded_allowed=step.degraded_allowed,
        created_at=step.created_at,
        updated_at=step.updated_at,
    )


def _row_to_step(row: ExecutionStepRow) -> Step:
    raw_type = row.type
    step_type: StepType | str
    try:
        step_type = StepType(raw_type)
    except ValueError:
        step_type = raw_type
    return Step(
        step_id=row.step_id,
        execution_id=row.execution_id,
        plan_id=row.plan_id,
        step_type=step_type,
        agent=row.agent,
        input=dict(row.input or {}),
        status=_step_status_from_str(row.status),
        dependencies=_dependencies_from_json(row.dependencies),
        retry_count=row.retry_count,
        degraded_allowed=row.degraded_allowed,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validation_outcome_from_json(raw: dict[str, Any] | None) -> ValidationOutcome | None:
    if raw is None:
        return None
    return ValidationOutcome.model_validate(raw)


def _validation_outcome_to_json(vo: ValidationOutcome | None) -> dict[str, Any] | None:
    if vo is None:
        return None
    return vo.model_dump(mode="json")


def _completeness_from_db(value: str | None) -> StepCompleteness | None:
    if value is None:
        return None
    return StepCompleteness(value)


def _completeness_to_db(value: StepCompleteness | None) -> str | None:
    if value is None:
        return None
    return value.value


def _apply_step_result_to_row(row: StepResultRow, result: StepResult) -> None:
    row.step_result_id = result.step_result_id
    row.step_id = result.step_id
    row.output = dict(result.output) if result.output is not None else None
    row.evidence = list(result.evidence)
    row.errors = list(result.errors)
    row.latency_ms = result.latency_ms
    row.latency_started_at = result.latency_started_at
    row.latency_ended_at = result.latency_ended_at
    row.confidence_score = result.confidence_score
    row.confidence_detail = dict(result.confidence_detail) if result.confidence_detail is not None else None
    row.completeness = _completeness_to_db(result.completeness)
    row.validation_outcome = _validation_outcome_to_json(result.validation_outcome)
    row.created_at = result.created_at
    row.updated_at = result.updated_at


def _row_to_step_result(row: StepResultRow) -> StepResult:
    return StepResult(
        step_result_id=row.step_result_id,
        step_id=row.step_id,
        output=dict(row.output) if row.output is not None else None,
        evidence=[dict(x) for x in (row.evidence or [])],
        errors=[dict(x) for x in (row.errors or [])],
        latency_ms=row.latency_ms,
        latency_started_at=row.latency_started_at,
        latency_ended_at=row.latency_ended_at,
        confidence_score=_confidence_to_python(row.confidence_score),
        confidence_detail=dict(row.confidence_detail) if row.confidence_detail is not None else None,
        completeness=_completeness_from_db(row.completeness),
        validation_outcome=_validation_outcome_from_json(
            dict(row.validation_outcome) if row.validation_outcome is not None else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresRepository:
    """PostgreSQL adapter: maps ORM rows to common_schemas models (no runtime logic)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_context(self, context: ExecutionContext) -> None:
        with self._session_factory() as session:
            session.merge(_context_to_row(context))
            session.commit()

    def get_context(self, context_id: UUID) -> ExecutionContext | None:
        with self._session_factory() as session:
            row = session.get(ExecutionContextRow, context_id)
            return _row_to_context(row) if row is not None else None

    def save_execution(self, execution: Execution) -> None:
        with self._session_factory() as session:
            session.merge(_execution_to_row(execution))
            session.commit()

    def get_execution(self, execution_id: UUID) -> Execution | None:
        with self._session_factory() as session:
            row = session.get(ExecutionRow, execution_id)
            return _row_to_execution(row) if row is not None else None

    def update_execution(self, execution: Execution) -> None:
        with self._session_factory() as session:
            existing = session.get(ExecutionRow, execution.execution_id)
            if existing is None:
                msg = f"execution {execution.execution_id} not found"
                raise KeyError(msg)
            merged = _execution_to_row(execution)
            for key in sa_inspect(merged).mapper.column_attrs.keys():
                setattr(existing, key, getattr(merged, key))
            session.commit()

    def save_plan(self, plan: ExecutionPlan) -> None:
        with self._session_factory() as session:
            session.merge(_plan_to_row(plan))
            session.commit()

    def get_plan(self, plan_id: UUID) -> ExecutionPlan | None:
        with self._session_factory() as session:
            row = session.get(ExecutionPlanRow, plan_id)
            return _row_to_plan(row) if row is not None else None

    def save_step(self, step: Step) -> None:
        with self._session_factory() as session:
            session.merge(_step_to_row(step))
            session.commit()

    def get_step(self, step_id: UUID) -> Step | None:
        with self._session_factory() as session:
            row = session.get(ExecutionStepRow, step_id)
            return _row_to_step(row) if row is not None else None

    def update_step(self, step: Step) -> None:
        with self._session_factory() as session:
            existing = session.get(ExecutionStepRow, step.step_id)
            if existing is None:
                msg = f"step {step.step_id} not found"
                raise KeyError(msg)
            merged = _step_to_row(step)
            for key in sa_inspect(merged).mapper.column_attrs.keys():
                setattr(existing, key, getattr(merged, key))
            session.commit()

    def list_steps_for_execution(self, execution_id: UUID) -> list[Step]:
        with self._session_factory() as session:
            stmt = (
                select(ExecutionStepRow)
                .where(ExecutionStepRow.execution_id == execution_id)
                .order_by(ExecutionStepRow.created_at.asc())
            )
            rows = session.scalars(stmt).all()
            return [_row_to_step(r) for r in rows]

    def save_step_result(self, result: StepResult) -> None:
        with self._session_factory() as session:
            existing = session.scalar(select(StepResultRow).where(StepResultRow.step_id == result.step_id))
            if existing is None:
                row = StepResultRow(
                    step_result_id=result.step_result_id,
                    step_id=result.step_id,
                )
                _apply_step_result_to_row(row, result)
                session.add(row)
            else:
                _apply_step_result_to_row(existing, result)
            session.commit()

    def get_step_result(self, step_id: UUID) -> StepResult | None:
        with self._session_factory() as session:
            row = session.scalar(select(StepResultRow).where(StepResultRow.step_id == step_id))
            return _row_to_step_result(row) if row is not None else None
