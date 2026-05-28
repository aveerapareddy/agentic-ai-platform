"""Cost attribution workflow structured contracts (Session D)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ExecutionId, StepId
from .reasoning import ModelInvocationTelemetry


class CostAttributionAnalysisModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    step_id: StepId
    scope_id: str = Field(max_length=256, description="Billing scope, account, or service group id.")
    workflow_type: str = Field(default="cost_attribution", max_length=64)
    execution_input_excerpt: dict[str, Any] = Field(default_factory=dict)


class CostAttributionReasoningOutput(BaseModel):
    """Analyze-step structured output."""

    model_config = ConfigDict(extra="forbid")

    suspected_service: str = Field(max_length=128)
    suspected_team: str = Field(max_length=128)
    anomaly_type: str = Field(max_length=64)
    estimated_cost_impact_usd: float = Field(ge=0.0)
    attribution_summary: str = Field(max_length=4000)
    optimization_candidates: list[str] = Field(default_factory=list, max_length=16)
    evidence_references: list[str] = Field(default_factory=list, max_length=32)
    model_invocation_id: str = Field(max_length=128)
    provider_label: str = Field(max_length=64)
    invocation: ModelInvocationTelemetry | None = None


class CostEvidenceSummary(BaseModel):
    """Retrieval/tool evidence rollup for cost workflows."""

    model_config = ConfigDict(extra="forbid")

    scope_id: str = Field(max_length=256)
    evidence_summary: str = Field(max_length=4000)
    chunk_ids: list[str] = Field(default_factory=list, max_length=64)
    retrieval_id: str | None = Field(default=None, max_length=128)
    corpus_version: str | None = Field(default=None, max_length=64)
    tool_signals: list[dict[str, Any]] = Field(default_factory=list, max_length=32)


class CostAttributionValidationModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    step_id: StepId
    scope_id: str = Field(max_length=256)
    prior_attribution_summary: str = Field(default="", max_length=2000)
    prior_evidence_summary: str = Field(default="", max_length=2000)
    prior_optimization_candidates: list[str] = Field(default_factory=list, max_length=16)


class CostValidationOutput(BaseModel):
    """Validation-step structured output."""

    model_config = ConfigDict(extra="forbid")

    validation_status: str = Field(max_length=32)
    confidence: float = Field(ge=0.0, le=1.0)
    likely_service: str = Field(max_length=128)
    likely_team: str = Field(max_length=128)
    rationale_short: str = Field(max_length=500)
    recommended_actions: list[str] = Field(default_factory=list, max_length=16)
    digest: str = Field(default="", max_length=64)
    model_invocation_id: str = Field(max_length=128)
    provider_label: str = Field(max_length=64)
    invocation: ModelInvocationTelemetry | None = None
