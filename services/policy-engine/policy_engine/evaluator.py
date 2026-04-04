"""Deterministic policy rules: explicit branching only, no DSL (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from common_schemas import (
    ActionProposal,
    ExecutionContext,
    PolicyDecision,
)

RULE_PACK_ID = "phase3_deterministic_v1"


@dataclass(frozen=True)
class PolicyEvaluationDraft:
    """Outcome of evaluation; orchestrator assigns ids and persists PolicyEvaluation rows."""

    decision: PolicyDecision
    reason: str
    evaluated_rules: list[dict[str, object]] = field(default_factory=list)


class PolicyEvaluator:
    """Evaluates a single action proposal against execution context facts."""

    def evaluate(self, *, context: ExecutionContext, proposal: ActionProposal) -> PolicyEvaluationDraft:
        """Return allow, deny, or conditional with auditable rule references."""
        rules: list[dict[str, object]] = []

        def hit(rule_id: str, detail: str) -> None:
            rules.append(
                {
                    "rule_id": rule_id,
                    "pack": RULE_PACK_ID,
                    "detail": detail,
                }
            )

        if proposal.action_type != "escalate_incident":
            hit("R_UNKNOWN_ACTION", "unsupported action type for Phase 3 pack")
            return PolicyEvaluationDraft(
                decision=PolicyDecision.DENY,
                reason="action_type not permitted by phase3_deterministic_v1",
                evaluated_rules=rules,
            )

        scope = context.policy_scope
        if scope == "phase3_deny":
            hit("R_SCOPE_DENY", "policy_scope phase3_deny blocks escalation")
            return PolicyEvaluationDraft(
                decision=PolicyDecision.DENY,
                reason="policy_scope explicitly denies escalation (phase3_deny)",
                evaluated_rules=rules,
            )

        if context.environment == "prod" or scope == "phase3_conditional":
            hit("R_CONDITIONAL_APPROVAL", "prod or phase3_conditional requires approval")
            return PolicyEvaluationDraft(
                decision=PolicyDecision.CONDITIONAL,
                reason="escalation requires human approval for this environment or policy_scope",
                evaluated_rules=rules,
            )

        hit("R_DEFAULT_ALLOW", "non-prod default allow for escalate_incident")
        return PolicyEvaluationDraft(
            decision=PolicyDecision.ALLOW,
            reason="escalation allowed without additional approval for this environment and policy_scope",
            evaluated_rules=rules,
        )
