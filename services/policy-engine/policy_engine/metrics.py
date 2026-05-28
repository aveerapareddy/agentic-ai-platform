"""Policy evaluation counters (side effects only; no policy logic)."""

from __future__ import annotations

from common_schemas import PolicyDecision


def record_policy_evaluation(decision: PolicyDecision) -> None:
    try:
        from observability.metrics import get_registry
    except ImportError:
        return
    reg = get_registry()
    reg.inc("policy_evaluations_total")
    if decision == PolicyDecision.ALLOW:
        reg.inc("policy_decision_allow_total")
    elif decision == PolicyDecision.DENY:
        reg.inc("policy_decision_deny_total")
    elif decision == PolicyDecision.CONDITIONAL:
        reg.inc("policy_decision_conditional_total")


def record_policy_simulation() -> None:
    try:
        from observability.metrics import get_registry
    except ImportError:
        return
    get_registry().inc("policy_simulations_total")
