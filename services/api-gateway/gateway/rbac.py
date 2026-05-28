"""Gateway RBAC: access checks only; policy decisions remain in policy-engine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from common_schemas import RequestContext, Role
from fastapi import Depends, Request

from gateway.auth import get_request_context
from gateway.http_errors import api_error


def require_any_role(*roles: Role) -> Callable[..., RequestContext]:
    """Dependency factory: caller must hold at least one allowed role."""

    def _dep(
        request: Request,
        ctx: Annotated[RequestContext, Depends(get_request_context)],
    ) -> RequestContext:
        if not ctx.has_any_role(*roles):
            allowed = ", ".join(r.value for r in roles)
            raise api_error(
                code="FORBIDDEN",
                message=f"requires one of roles: {allowed}",
                status_code=403,
                request=request,
            )
        return ctx

    return _dep


ExecutionsReadDep = Annotated[
    RequestContext,
    Depends(require_any_role(Role.VIEWER, Role.OPERATOR, Role.APPROVER, Role.ADMIN)),
]
ExecutionsWriteDep = Annotated[
    RequestContext,
    Depends(require_any_role(Role.OPERATOR, Role.ADMIN)),
]
ApprovalsWriteDep = Annotated[
    RequestContext,
    Depends(require_any_role(Role.APPROVER, Role.ADMIN)),
]
PoliciesAdminDep = Annotated[RequestContext, Depends(require_any_role(Role.ADMIN))]

# Business metrics and insights (same read roles as executions/trace).
MetricsReadDep = ExecutionsReadDep
InsightsReadDep = ExecutionsReadDep
