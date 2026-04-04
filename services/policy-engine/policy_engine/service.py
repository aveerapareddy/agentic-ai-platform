"""Thin façade: orchestrator calls this; service does not persist or mutate executions."""

from __future__ import annotations

from common_schemas import ActionProposal, ExecutionContext

from policy_engine.evaluator import PolicyEvaluationDraft, PolicyEvaluator


class PolicyEvaluationService:
    """Synchronous policy evaluation entrypoint (no tool execution, no execution graph)."""

    def __init__(self, evaluator: PolicyEvaluator | None = None) -> None:
        self._evaluator = evaluator or PolicyEvaluator()

    def evaluate_proposal(
        self,
        context: ExecutionContext,
        proposal: ActionProposal,
    ) -> PolicyEvaluationDraft:
        return self._evaluator.evaluate(context=context, proposal=proposal)
