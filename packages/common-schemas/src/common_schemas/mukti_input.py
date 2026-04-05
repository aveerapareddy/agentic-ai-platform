"""Frozen snapshot for post-execution Mukti analysis (no live execution control)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .execution import Execution
from .feedback import OperatorFeedback
from .policy import ActionProposal, PolicyEvaluation
from .workflow import Step, StepResult


class StepRunRecord(BaseModel):
    """One step plus its persisted result for Mukti consumption."""

    model_config = ConfigDict(extra="forbid")

    step: Step
    result: StepResult | None = None


class MuktiAnalysisInput(BaseModel):
    """Structured inputs only; built from stored execution artifacts post-termination."""

    model_config = ConfigDict(extra="forbid")

    execution: Execution
    step_records: list[StepRunRecord] = Field(default_factory=list)
    operator_feedback: list[OperatorFeedback] = Field(default_factory=list)
    policy_evaluations: list[PolicyEvaluation] = Field(default_factory=list)
    action_proposals: list[ActionProposal] = Field(default_factory=list)
