"""Policy evaluations, approvals, and action proposals (governance path)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .ids import ActionId, ApprovalId, ContextId, ExecutionId, PolicyEvaluationId, StepId


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionProposalStatus(StrEnum):
    PROPOSED = "proposed"
    POLICY_DENIED = "policy_denied"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class PolicyEvaluation(BaseModel):
    """Policy engine outcome; agents supply facts, not decisions."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: PolicyEvaluationId
    execution_id: ExecutionId
    execution_context_id: ContextId
    decision: PolicyDecision
    reason: str
    evaluated_rules: list[dict[str, Any]] = Field(default_factory=list)
    subject_ref: dict[str, Any] = Field(
        default_factory=dict,
        description="Evaluated subject, e.g. proposal_id or tool_call_id keyed structure.",
    )
    created_at: datetime
    updated_at: datetime


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


class Approval(BaseModel):
    """Human or delegated approval on a proposal or conditional policy outcome."""

    model_config = ConfigDict(extra="forbid")

    approval_id: ApprovalId
    execution_id: ExecutionId
    policy_evaluation_id: PolicyEvaluationId | None = None
    action_proposal_id: ActionId | None = None
    approver: str
    decision: ApprovalDecision
    notes: str | None = None
    decided_at: datetime
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def require_evaluation_or_proposal(self) -> Approval:
        if self.policy_evaluation_id is None and self.action_proposal_id is None:
            msg = "approval requires policy_evaluation_id and/or action_proposal_id"
            raise ValueError(msg)
        return self


class ActionProposal(BaseModel):
    """Intent to mutate external state; execution awaits policy and optional approval."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: ActionId
    execution_id: ExecutionId
    step_id: StepId | None = None
    action_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    requires_approval: bool = False
    status: ActionProposalStatus
    created_at: datetime
    updated_at: datetime
