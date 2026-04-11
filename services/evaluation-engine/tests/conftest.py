"""Shared fakes implementing ExecutionDataPort."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from common_schemas import (
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionStatus,
    PolicyDecision,
    PolicyEvaluation,
    Step,
    StepResult,
    StepStatus,
    StepType,
    ToolCall,
    ToolCallStatus,
    ToolIdempotency,
    ToolSideEffectClass,
)


@dataclass
class FakeStore:
    contexts: dict[UUID, ExecutionContext] = field(default_factory=dict)
    executions: dict[UUID, Execution] = field(default_factory=dict)
    steps: dict[UUID, list[Step]] = field(default_factory=dict)
    step_results: dict[UUID, StepResult] = field(default_factory=dict)
    tool_calls: dict[UUID, list[ToolCall]] = field(default_factory=dict)
    policy_evals: dict[UUID, list[PolicyEvaluation]] = field(default_factory=dict)

    def get_execution(self, execution_id: UUID) -> Execution | None:
        return self.executions.get(execution_id)

    def get_context(self, context_id: UUID) -> ExecutionContext | None:
        return self.contexts.get(context_id)

    def list_steps_for_execution(self, execution_id: UUID) -> list[Step]:
        return list(self.steps.get(execution_id, []))

    def get_step_result(self, step_id: UUID) -> StepResult | None:
        return self.step_results.get(step_id)

    def list_tool_calls_for_step(self, step_id: UUID) -> list[ToolCall]:
        return list(self.tool_calls.get(step_id, []))

    def list_policy_evaluations_for_execution(self, execution_id: UUID) -> list[PolicyEvaluation]:
        return list(self.policy_evals.get(execution_id, []))

    def list_executions(
        self,
        *,
        tenant_id: str | None = None,
        workflow_type: str | None = None,
        status: ExecutionStatus | str | None = None,
        limit: int = 50,
    ) -> list[Execution]:
        out = list(self.executions.values())
        if tenant_id is not None:
            ctx_ids = {c.context_id for c in self.contexts.values() if c.tenant_id == tenant_id}
            out = [e for e in out if e.execution_context_id in ctx_ids]
        if workflow_type is not None:
            out = [e for e in out if e.workflow_type == workflow_type]
        if status is not None:
            st = status.value if hasattr(status, "value") else status
            out = [e for e in out if e.status.value == st]
        out.sort(key=lambda e: e.created_at)
        return out[:limit]


def utc() -> datetime:
    return datetime.now(timezone.utc)
