"""Bounded structured contracts for model-runtime reasoning (Phase 5).

Outputs are validated at the boundary; orchestrator never treats raw model text as authoritative state.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import ExecutionId, StepId


class IncidentAnalysisModelRequest(BaseModel):
    """Inputs for analyze_incident; no prompt blobs—structured facts only."""

    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    step_id: StepId
    incident_id: str = Field(max_length=256)
    workflow_type: str = Field(default="incident_triage", max_length=64)
    execution_input_excerpt: dict[str, Any] = Field(
        default_factory=dict,
        description="Small subset of execution.input (e.g. severity); must stay bounded by caller.",
    )


class IncidentAnalysisReasoningOutput(BaseModel):
    """Structured analyze step artifact; maps to gather_analyze StepResult.output keys."""

    model_config = ConfigDict(extra="forbid")

    incident_summary: str = Field(max_length=4000)
    possible_causes: list[str] = Field(default_factory=list, max_length=16)
    model_invocation_id: str = Field(max_length=128)
    provider_label: str = Field(max_length=64)


class IncidentValidationModelRequest(BaseModel):
    """Inputs for validate_incident; incorporates prior step outputs as structured fields only."""

    model_config = ConfigDict(extra="forbid")

    execution_id: ExecutionId
    step_id: StepId
    incident_id: str = Field(max_length=256)
    prior_possible_causes: list[str] = Field(default_factory=list, max_length=16)
    prior_incident_summary_excerpt: str = Field(default="", max_length=2000)
    evidence_summary_excerpt: str = Field(default="", max_length=2000)


class IncidentValidationReasoningOutput(BaseModel):
    """Structured validate step artifact; aligns with validate_incident StepResult.output."""

    model_config = ConfigDict(extra="forbid")

    likely_cause: str = Field(max_length=128)
    validation_status: str = Field(max_length=32)
    confidence_score: float = Field(ge=0.0, le=1.0)
    rationale_short: str = Field(max_length=500)
    digest: str = Field(default="", max_length=64)
    model_invocation_id: str = Field(max_length=128)
    provider_label: str = Field(max_length=64)
