"""Deterministic policy rule descriptors (read-only catalog)."""

from __future__ import annotations

from common_schemas import PolicyRuleDescriptor

from policy_engine.evaluator import RULE_PACK_ID

POLICY_RULE_DESCRIPTORS: tuple[PolicyRuleDescriptor, ...] = (
    PolicyRuleDescriptor(
        rule_id="R_UNKNOWN_ACTION",
        description="Reject action types not registered in the phase3 deterministic pack.",
        applies_to=["*"],
        decision="deny",
        reason="action_type not permitted by phase3_deterministic_v1",
    ),
    PolicyRuleDescriptor(
        rule_id="R_SCOPE_DENY",
        description="Explicit policy_scope blocks escalation.",
        applies_to=["escalate_incident"],
        decision="deny",
        reason="policy_scope explicitly denies escalation",
    ),
    PolicyRuleDescriptor(
        rule_id="R_CONDITIONAL_APPROVAL",
        description="Production environment or conditional scope requires human approval.",
        applies_to=["escalate_incident"],
        decision="conditional",
        reason="escalation requires human approval for this environment or policy_scope",
    ),
    PolicyRuleDescriptor(
        rule_id="R_DEFAULT_ALLOW",
        description="Non-production default allow for escalate_incident.",
        applies_to=["escalate_incident"],
        decision="allow",
        reason="escalation allowed without additional approval",
    ),
)


def list_rule_descriptors() -> list[PolicyRuleDescriptor]:
    return list(POLICY_RULE_DESCRIPTORS)


def rule_pack_id() -> str:
    return RULE_PACK_ID
