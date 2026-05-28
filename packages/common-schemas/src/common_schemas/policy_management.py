"""Policy inspection and simulation contracts (gateway ↔ policy-engine)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .policy import PolicyDecision, RiskLevel


class PolicyRuleDescriptor(BaseModel):
    """Static rule metadata for operators and simulation audit."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(max_length=64)
    description: str = Field(max_length=500)
    applies_to: list[str] = Field(default_factory=list, max_length=32)
    decision: str = Field(
        max_length=32,
        description="Typical outcome when rule matches: allow, deny, conditional, or evaluate.",
    )
    reason: str = Field(max_length=500)


class PolicySimulateRequest(BaseModel):
    """What-if evaluation; does not mutate rule packs."""

    model_config = ConfigDict(extra="forbid")

    action_type: str = Field(max_length=128)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    execution_context: dict[str, Any] = Field(
        default_factory=dict,
        description="environment, policy_scope; tenant/principal come from trusted gateway context.",
    )
    feature_flags: dict[str, Any] | None = None


class PolicySimulateResult(BaseModel):
    """Structured simulation outcome."""

    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecision
    reason: str = Field(max_length=2000)
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    rule_references: list[str] = Field(default_factory=list, max_length=64)
    rule_pack_id: str = Field(max_length=64)
