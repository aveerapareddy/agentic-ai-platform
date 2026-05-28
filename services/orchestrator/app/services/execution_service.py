"""Create, fetch, start, enqueue, and cancel executions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from common_schemas import (
    ApprovalDecision,
    ContextId,
    Execution,
    ExecutionContext,
    ExecutionId,
    ExecutionMode,
    ExecutionStatus,
)

from app.adapters.repository import Repository
from app.runtime.orchestrator import ExecutionEngine, OrchestrationError, cancel_execution, fail_execution
from app.runtime.queue import InMemoryExecutionQueue
from app.runtime.runtime_meta import mark_queued, mark_worker_started, request_cancellation_meta


class ExecutionService:
    """Coordinates persistence, queueing, and the execution engine."""

    def __init__(
        self,
        repository: Repository,
        engine: ExecutionEngine | None = None,
        *,
        queue: InMemoryExecutionQueue | None = None,
    ) -> None:
        self._repo = repository
        self._engine = engine or ExecutionEngine(repository)
        self._queue = queue or InMemoryExecutionQueue()

    @property
    def queue(self) -> InMemoryExecutionQueue:
        return self._queue

    def create_execution(
        self,
        *,
        workflow_type: str,
        input_payload: dict[str, Any],
        tenant_id: str,
        request_id: str,
        environment: str,
        policy_scope: str,
        principal_id: str | None = None,
        execution_mode: ExecutionMode = ExecutionMode.BACKGROUND,
        permissions_scope: dict[str, Any] | None = None,
        parent_execution_id: ExecutionId | None = None,
        feature_flags: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> Execution:
        """Persist a new execution in CREATED with a fresh execution context."""
        ts = now or datetime.now(timezone.utc)
        context_id: ContextId = uuid4()
        execution_id: ExecutionId = uuid4()

        ctx = ExecutionContext(
            context_id=context_id,
            tenant_id=tenant_id,
            principal_id=principal_id,
            request_id=request_id,
            environment=environment,
            permissions_scope=permissions_scope or {},
            policy_scope=policy_scope,
            feature_flags=feature_flags,
            created_at=ts,
            updated_at=ts,
        )
        self._repo.save_context(ctx)

        execution = Execution(
            execution_id=execution_id,
            workflow_type=workflow_type,
            status=ExecutionStatus.CREATED,
            execution_mode=execution_mode,
            execution_context_id=context_id,
            parent_execution_id=parent_execution_id,
            input=dict(input_payload),
            created_at=ts,
            updated_at=ts,
        )
        self._repo.save_execution(execution)
        return execution

    def get_execution(self, execution_id: UUID) -> Execution | None:
        return self._repo.get_execution(execution_id)

    def list_executions(
        self,
        *,
        tenant_id: str | None = None,
        workflow_type: str | None = None,
        status: ExecutionStatus | str | None = None,
        limit: int = 50,
    ) -> list[Execution]:
        return self._repo.list_executions(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=status,
            limit=limit,
        )

    def enqueue_execution(self, execution_id: UUID, *, now: datetime | None = None) -> Execution:
        """Queue execution for worker processing (background mode)."""
        ts = now or datetime.now(timezone.utc)
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            raise KeyError(execution_id)
        ex = mark_queued(ex, at=ts)
        self._repo.update_execution(ex)
        depth = self._queue.enqueue(execution_id, now=ts)
        try:
            from observability import emit_event, get_registry

            get_registry().inc("execution_enqueued_total")
            get_registry().observe_latency_ms("execution_queue_depth", float(depth), labels={})
            emit_event("execution_enqueued", execution_id=str(execution_id), queue_depth=depth)
        except ImportError:
            pass
        return ex

    def start_execution(self, execution_id: UUID) -> Execution:
        """Run the orchestration loop until a terminal execution status (synchronous path)."""
        try:
            return self._engine.run_execution(execution_id)
        except OrchestrationError as e:
            return fail_execution(self._repo, execution_id, reason=str(e))

    def record_worker_started(self, execution_id: UUID, *, worker_id: str, now: datetime | None = None) -> Execution:
        ts = now or datetime.now(timezone.utc)
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            raise KeyError(execution_id)
        ex = mark_worker_started(ex, worker_id=worker_id, at=ts)
        self._repo.update_execution(ex)
        return ex

    def request_cancellation(self, execution_id: UUID, *, reason: str = "operator") -> Execution:
        """Request cancellation; worker/orchestrator loop stops at next safe boundary."""
        ts = datetime.now(timezone.utc)
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            raise KeyError(execution_id)
        ex = request_cancellation_meta(ex, at=ts, reason=reason)
        self._repo.update_execution(ex)
        if ex.status in {
            ExecutionStatus.CREATED,
            ExecutionStatus.PLANNING,
            ExecutionStatus.EXECUTING,
            ExecutionStatus.VALIDATING,
            ExecutionStatus.AWAITING_APPROVAL,
        }:
            return cancel_execution(self._repo, execution_id, reason=reason, now=ts)
        return ex

    def submit_approval(
        self,
        execution_id: UUID,
        *,
        approver: str,
        decision: ApprovalDecision,
        notes: str | None = None,
    ) -> Execution:
        """Record approval for executions in AWAITING_APPROVAL (Phase 3 incident triage)."""
        return self._engine.submit_approval(
            execution_id,
            approver=approver,
            decision=decision,
            notes=notes,
        )
