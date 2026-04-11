"""Structured evaluation outputs (all derived from stored execution artifacts)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionMetrics(BaseModel):
    """Per-execution metrics computed from trace, steps, results, tools, and policy rows."""

    model_config = ConfigDict(extra="forbid")

    execution_id: str
    workflow_type: str
    execution_status: str
    tenant_id: str | None = None

    model_reasoning_event_count: int = Field(
        ge=0,
        description="Count of trace timeline rows with event_type=model_reasoning.",
    )
    model_reasoning_fallback_event_count: int = Field(
        ge=0,
        description="Subset with path=deterministic_fallback (stored trace vocabulary).",
    )
    model_fallback_rate: float | None = Field(
        default=None,
        description="fallback_event_count / model_reasoning_event_count; None if no model_reasoning events.",
    )

    validation_success: bool | None = Field(
        default=None,
        description="True/False from validation step results or validation_summary; None if indeterminate.",
    )
    validation_detail: str | None = Field(
        default=None,
        description="Short human-readable basis (e.g. outcome status or missing validation step).",
    )

    policy_decisions: list[str] = Field(
        default_factory=list,
        description="Policy evaluation decisions in chronological order (allow/deny/conditional).",
    )
    primary_policy_decision: str | None = Field(
        default=None,
        description="Last policy decision in scope, if any.",
    )

    tool_calls_total: int = Field(default=0, ge=0)
    tool_calls_success: int = Field(default=0, ge=0)
    tool_success_rate: float | None = Field(
        default=None,
        description="successes / total tool calls for this execution; None if no tool calls.",
    )

    step_latency_sum_ms: int | None = Field(
        default=None,
        description="Sum of step_result.latency_ms where present.",
    )
    wall_clock_ms: int | None = Field(
        default=None,
        description="completed_at - created_at when both present, in milliseconds.",
    )

    computation_notes: list[str] = Field(
        default_factory=list,
        description="Explicit notes on how fields were derived (explainability).",
    )


class WorkflowTypeRollup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_count: int = Field(ge=0)
    failed_execution_count: int = Field(ge=0)
    mean_model_fallback_rate: float | None = None
    mean_tool_success_rate: float | None = None
    policy_decision_counts: dict[str, int] = Field(default_factory=dict)


class StepTypeRollup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_count: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    model_reasoning_events: int = Field(ge=0)
    model_fallback_events: int = Field(ge=0)


class ToolNameRollup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invocations: int = Field(ge=0)
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)


class PolicyDecisionRollup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_count: int = Field(ge=0)
    distinct_execution_count: int = Field(
        ge=0,
        description="Executions that had at least one evaluation with this decision.",
    )


class AggregatedMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executions_in_scope: int = Field(ge=0)
    by_workflow_type: dict[str, WorkflowTypeRollup] = Field(default_factory=dict)
    by_step_type: dict[str, StepTypeRollup] = Field(default_factory=dict)
    by_tool_name: dict[str, ToolNameRollup] = Field(default_factory=dict)
    by_policy_decision: dict[str, PolicyDecisionRollup] = Field(default_factory=dict)


class AnomalyFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: str = Field(description="warning | elevated")
    explanation: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope_description: str
    execution_sample_size: int = Field(ge=0)
    aggregated: AggregatedMetrics
    anomalies: list[AnomalyFinding] = Field(default_factory=list)
    evaluation_score: float | None = Field(
        default=None,
        description=(
            "Deterministic scalar from documented formula over aggregated means "
            "(not model-based); None if insufficient data."
        ),
    )
    score_formula_notes: str | None = Field(
        default=None,
        description="Human-readable description of how evaluation_score was computed.",
    )
