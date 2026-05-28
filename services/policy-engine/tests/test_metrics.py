"""Policy evaluation observability counters."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
OBS_SRC = ROOT / "packages" / "observability" / "src"
if str(OBS_SRC) not in sys.path:
    sys.path.insert(0, str(OBS_SRC))

from common_schemas import PolicyDecision
from observability.metrics import get_registry
from policy_engine.metrics import record_policy_evaluation
from policy_engine.service import PolicyEvaluationService


def test_record_policy_evaluation_counters() -> None:
    reg = get_registry()
    reg.reset()
    record_policy_evaluation(PolicyDecision.ALLOW)
    record_policy_evaluation(PolicyDecision.DENY)
    record_policy_evaluation(PolicyDecision.CONDITIONAL)
    snap = reg.snapshot()["counters"]
    assert snap[("policy_evaluations_total", ())] == 3
    assert snap[("policy_decision_allow_total", ())] == 1
    assert snap[("policy_decision_deny_total", ())] == 1
    assert snap[("policy_decision_conditional_total", ())] == 1


def test_simulate_increments_simulation_counter() -> None:
    from common_schemas import PolicySimulateRequest, RiskLevel

    reg = get_registry()
    reg.reset()
    svc = PolicyEvaluationService()
    svc.simulate_policy(
        PolicySimulateRequest(
            action_type="escalate_incident",
            risk_level=RiskLevel.HIGH,
            execution_context={"environment": "dev", "policy_scope": "default"},
        ),
        tenant_id="t1",
    )
    snap = reg.snapshot()["counters"]
    assert snap.get(("policy_simulations_total", ()), 0) >= 1
    assert snap.get(("policy_evaluations_total", ()), 0) >= 1
