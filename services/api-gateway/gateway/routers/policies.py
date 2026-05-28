from __future__ import annotations

from fastapi import APIRouter, Request

from common_schemas import PolicySimulateRequest

from gateway.dependencies import PolicyFacadeDep
from gateway.http_errors import api_error
from gateway.rbac import PoliciesAdminDep
from gateway.schemas.policy import PolicyListResponse, PolicySimulateResponse

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
def list_policies(
    _auth: PoliciesAdminDep,
    facade: PolicyFacadeDep,
) -> PolicyListResponse:
    pack_id, rules = facade.list_rules()
    return PolicyListResponse(rule_pack_id=pack_id, rules=rules)


@router.post("/simulate", response_model=PolicySimulateResponse)
def simulate_policy(
    body: PolicySimulateRequest,
    request: Request,
    auth: PoliciesAdminDep,
    facade: PolicyFacadeDep,
) -> PolicySimulateResponse:
    if not body.execution_context.get("policy_scope"):
        raise api_error(
            code="VALIDATION_ERROR",
            message="execution_context.policy_scope is required",
            status_code=400,
            request=request,
        )
    try:
        result = facade.simulate(body, auth)
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e
    return PolicySimulateResponse.from_result(result)
