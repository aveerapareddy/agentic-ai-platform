"""Expose policy-engine read/simulate capabilities; no rule mutation."""

from __future__ import annotations

from common_schemas import PolicyRuleDescriptor, PolicySimulateRequest, PolicySimulateResult, RequestContext

from policy_engine.service import PolicyEvaluationService


class PolicyFacade:
    def __init__(self, policy_service: PolicyEvaluationService | None = None) -> None:
        self._policy = policy_service or PolicyEvaluationService()

    def list_rules(self) -> tuple[str, list[PolicyRuleDescriptor]]:
        return self._policy.rule_pack_id(), self._policy.list_rule_descriptors()

    def simulate(
        self,
        body: PolicySimulateRequest,
        auth: RequestContext,
    ) -> PolicySimulateResult:
        return self._policy.simulate_policy(
            body,
            tenant_id=auth.tenant.tenant_id,
            principal_id=auth.principal.principal_id,
            request_id=auth.request_id,
        )
