"""Policy evaluator paths."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import (
    ActionProposal,
    ActionProposalStatus,
    ExecutionContext,
    ExecutionId,
    PolicyDecision,
    RiskLevel,
    StepId,
)

from policy_engine.evaluator import PolicyEvaluator


def _ctx(*, env: str = "dev", policy_scope: str = "default") -> ExecutionContext:
    now = datetime.now(timezone.utc)
    return ExecutionContext(
        context_id=uuid4(),
        tenant_id="t",
        request_id="r",
        environment=env,
        permissions_scope={},
        policy_scope=policy_scope,
        created_at=now,
        updated_at=now,
    )


def _proposal(eid: ExecutionId, *, step_id: StepId | None = None) -> ActionProposal:
    now = datetime.now(timezone.utc)
    return ActionProposal(
        proposal_id=uuid4(),
        execution_id=eid,
        step_id=step_id,
        action_type="escalate_incident",
        payload={"severity": "high"},
        risk_level=RiskLevel.HIGH,
        requires_approval=False,
        status=ActionProposalStatus.PROPOSED,
        created_at=now,
        updated_at=now,
    )


def test_policy_allow_default() -> None:
    ev = PolicyEvaluator()
    eid: ExecutionId = uuid4()
    d = ev.evaluate(context=_ctx(), proposal=_proposal(eid))
    assert d.decision == PolicyDecision.ALLOW


def test_policy_conditional_prod() -> None:
    ev = PolicyEvaluator()
    eid: ExecutionId = uuid4()
    d = ev.evaluate(context=_ctx(env="prod"), proposal=_proposal(eid))
    assert d.decision == PolicyDecision.CONDITIONAL


def test_policy_conditional_scope() -> None:
    ev = PolicyEvaluator()
    eid: ExecutionId = uuid4()
    d = ev.evaluate(context=_ctx(policy_scope="phase3_conditional"), proposal=_proposal(eid))
    assert d.decision == PolicyDecision.CONDITIONAL


def test_policy_deny_scope() -> None:
    ev = PolicyEvaluator()
    eid: ExecutionId = uuid4()
    d = ev.evaluate(context=_ctx(policy_scope="phase3_deny"), proposal=_proposal(eid))
    assert d.decision == PolicyDecision.DENY


def test_policy_deny_unknown_action() -> None:
    ev = PolicyEvaluator()
    now = datetime.now(timezone.utc)
    eid: ExecutionId = uuid4()
    p = ActionProposal(
        proposal_id=uuid4(),
        execution_id=eid,
        action_type="arbitrary_mutation",
        payload={},
        risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
        status=ActionProposalStatus.PROPOSED,
        created_at=now,
        updated_at=now,
    )
    d = ev.evaluate(context=_ctx(), proposal=p)
    assert d.decision == PolicyDecision.DENY
