"""Policy rule descriptors and simulation."""

from __future__ import annotations

from common_schemas import PolicyDecision, PolicySimulateRequest, RiskLevel

from policy_engine.rules import list_rule_descriptors, rule_pack_id
from policy_engine.service import PolicyEvaluationService


def test_rule_descriptors_present() -> None:
    rules = list_rule_descriptors()
    assert len(rules) >= 4
    ids = {r.rule_id for r in rules}
    assert "R_DEFAULT_ALLOW" in ids
    assert rule_pack_id() == "phase3_deterministic_v1"


def test_simulate_policy_paths() -> None:
    svc = PolicyEvaluationService()
    allow = svc.simulate_policy(
        PolicySimulateRequest(
            action_type="escalate_incident",
            risk_level=RiskLevel.HIGH,
            execution_context={"environment": "dev", "policy_scope": "default"},
        ),
        tenant_id="t1",
        principal_id="p1",
    )
    assert allow.decision == PolicyDecision.ALLOW
    assert allow.rule_references

    deny = svc.simulate_policy(
        PolicySimulateRequest(
            action_type="escalate_incident",
            execution_context={"environment": "dev", "policy_scope": "phase3_deny"},
        ),
        tenant_id="t1",
    )
    assert deny.decision == PolicyDecision.DENY
