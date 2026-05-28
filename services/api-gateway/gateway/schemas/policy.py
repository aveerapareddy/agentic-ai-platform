from __future__ import annotations

from common_schemas import PolicyRuleDescriptor, PolicySimulateRequest, PolicySimulateResult
from pydantic import BaseModel, ConfigDict, Field


class PolicyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_pack_id: str
    rules: list[PolicyRuleDescriptor]


class PolicySimulateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    reason: str
    matched_rules: list[dict]
    rule_references: list[str]
    rule_pack_id: str

    @classmethod
    def from_result(cls, result: PolicySimulateResult) -> PolicySimulateResponse:
        return cls(
            decision=result.decision.value,
            reason=result.reason,
            matched_rules=list(result.matched_rules),
            rule_references=list(result.rule_references),
            rule_pack_id=result.rule_pack_id,
        )


# Re-export request body type for OpenAPI
PolicySimulateBody = PolicySimulateRequest
