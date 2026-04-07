"""Create, fetch, and start executions (Phase 1)."""

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
from app.runtime.orchestrator import ExecutionEngine, OrchestrationError, fail_execution


class ExecutionService:
    """Coordinates persistence and the execution engine.

    `repository` may be InMemoryRepository, PostgresRepository, or any other `Repository` implementation.
    """

    def __init__(self, repository: Repository, engine: ExecutionEngine | None = None) -> None:
        self._repo = repository
        self._engine = engine or ExecutionEngine(repository)

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

    def start_execution(self, execution_id: UUID) -> Execution:
        """Run the orchestration loop until a terminal execution status."""
        try:
            return self._engine.run_execution(execution_id)
        except OrchestrationError as e:
            return fail_execution(self._repo, execution_id, reason=str(e))

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
