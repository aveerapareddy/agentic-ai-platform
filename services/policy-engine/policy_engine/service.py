"""Thin façade: orchestrator calls this; service does not persist or mutate executions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    ActionProposal,
    ActionProposalStatus,
    ExecutionContext,
    ExecutionId,
    PolicyRuleDescriptor,
    PolicySimulateRequest,
    PolicySimulateResult,
    RiskLevel,
)

from policy_engine.evaluator import PolicyEvaluationDraft, PolicyEvaluator
from policy_engine.metrics import record_policy_evaluation, record_policy_simulation
from policy_engine.rules import list_rule_descriptors, rule_pack_id


class PolicyEvaluationService:
    """Synchronous policy evaluation entrypoint (no tool execution, no execution graph)."""

    def __init__(self, evaluator: PolicyEvaluator | None = None) -> None:
        self._evaluator = evaluator or PolicyEvaluator()

    def list_rule_descriptors(self) -> list[PolicyRuleDescriptor]:
        return list_rule_descriptors()

    def rule_pack_id(self) -> str:
        return rule_pack_id()

    def evaluate_proposal(
        self,
        context: ExecutionContext,
        proposal: ActionProposal,
    ) -> PolicyEvaluationDraft:
        draft = self._evaluator.evaluate(context=context, proposal=proposal)
        record_policy_evaluation(draft.decision)
        return draft

    def simulate_policy(
        self,
        request: PolicySimulateRequest,
        *,
        tenant_id: str,
        principal_id: str | None = None,
        request_id: str = "policy-simulate",
    ) -> PolicySimulateResult:
        """Run evaluator logic without persisting; tenant/principal are trusted gateway inputs."""
        ctx_fields = dict(request.execution_context)
        environment = str(ctx_fields.get("environment") or "dev")
        policy_scope = str(ctx_fields.get("policy_scope") or "default")
        now = datetime.now(timezone.utc)
        context = ExecutionContext(
            context_id=uuid4(),
            tenant_id=tenant_id,
            principal_id=principal_id,
            request_id=request_id,
            environment=environment,
            permissions_scope={},
            policy_scope=policy_scope,
            feature_flags=request.feature_flags,
            created_at=now,
            updated_at=now,
        )
        eid: ExecutionId = uuid4()
        proposal = ActionProposal(
            proposal_id=uuid4(),
            execution_id=eid,
            action_type=request.action_type,
            payload={"simulated": True, "risk_level": request.risk_level.value},
            risk_level=request.risk_level,
            requires_approval=False,
            status=ActionProposalStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        draft = self._evaluator.evaluate(context=context, proposal=proposal)
        record_policy_simulation()
        record_policy_evaluation(draft.decision)
        refs = [str(r.get("rule_id")) for r in draft.evaluated_rules if r.get("rule_id")]
        return PolicySimulateResult(
            decision=draft.decision,
            reason=draft.reason,
            matched_rules=list(draft.evaluated_rules),
            rule_references=refs,
            rule_pack_id=rule_pack_id(),
        )
