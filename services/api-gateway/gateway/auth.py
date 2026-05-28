"""Header-based auth for local/dev; production attaches stronger identity at the edge."""

from __future__ import annotations

from typing import Annotated

from common_schemas import Principal, RequestContext, Role, TenantContext
from fastapi import Depends, Request

from gateway.config import Settings
from gateway.dependencies import GatewayState, get_state
from gateway.http_errors import api_error


def _parse_roles(raw: str | None) -> list[Role]:
    if not raw or not raw.strip():
        return []
    out: list[Role] = []
    for part in raw.split(","):
        token = part.strip().lower()
        if not token:
            continue
        try:
            out.append(Role(token))
        except ValueError:
            continue
    return out


def resolve_request_context(request: Request, settings: Settings) -> RequestContext:
    """Build trusted request context from headers or explicit dev fallback."""
    principal_hdr = request.headers.get("x-principal-id")
    tenant_hdr = request.headers.get("x-tenant-id")
    roles_hdr = request.headers.get("x-roles")
    request_id = request.headers.get("x-request-id") or "gateway"

    if principal_hdr and tenant_hdr:
        roles = _parse_roles(roles_hdr)
        if not roles:
            roles = [Role.VIEWER]
        principal = Principal(principal_id=principal_hdr.strip(), roles=roles)
        tenant = TenantContext(tenant_id=tenant_hdr.strip())
        return RequestContext(
            principal=principal,
            tenant=tenant,
            request_id=request_id,
            permissions_scope={"roles": [r.value for r in roles]},
        )

    if settings.allow_dev_principal_fallback:
        roles = _parse_roles(settings.dev_roles) or [Role.OPERATOR]
        return RequestContext(
            principal=Principal(principal_id=settings.dev_principal_id, roles=roles),
            tenant=TenantContext(tenant_id=settings.dev_tenant_id),
            request_id=request_id,
            permissions_scope={"roles": [r.value for r in roles]},
        )

    raise api_error(
        code="UNAUTHORIZED",
        message="Missing X-Principal-Id and X-Tenant-Id; dev fallback disabled",
        status_code=401,
        request=request,
    )


def get_request_context(
    request: Request,
    state: Annotated[GatewayState, Depends(get_state)],
) -> RequestContext:
    return resolve_request_context(request, state.settings)


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
