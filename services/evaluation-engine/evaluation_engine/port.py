"""Read-only port for persisted execution data; implemented by orchestrator repositories."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from common_schemas import Execution, ExecutionContext, PolicyEvaluation, Step, StepResult, ToolCall
from pydantic import BaseModel, ConfigDict, Field


class ExecutionDataPort(Protocol):
    """Minimal surface to compute metrics without duplicating orchestration logic."""

    def get_execution(self, execution_id: UUID) -> Execution | None: ...

    def get_context(self, context_id: UUID) -> ExecutionContext | None: ...

    def list_steps_for_execution(self, execution_id: UUID) -> list[Step]: ...

    def get_step_result(self, step_id: UUID) -> StepResult | None: ...

    def list_tool_calls_for_step(self, step_id: UUID) -> list[ToolCall]: ...

    def list_policy_evaluations_for_execution(self, execution_id: UUID) -> list[PolicyEvaluation]: ...

    def list_executions(
        self,
        *,
        tenant_id: str | None = None,
        workflow_type: str | None = None,
        status: Any | None = None,
        limit: int = 50,
    ) -> list[Execution]: ...


class AggregatedMetricFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = None
    workflow_type: str | None = None
    status: Any | None = Field(
        default=None,
        description="ExecutionStatus or string; forwarded to store list_executions.",
    )
    limit: int = Field(default=200, ge=1, le=10_000)
