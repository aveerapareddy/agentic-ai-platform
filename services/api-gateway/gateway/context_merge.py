"""Merge client execution context with trusted gateway auth; block tenant override."""

from __future__ import annotations

from typing import Any

from common_schemas import RequestContext


def merge_execution_context(
    client_context: dict[str, Any],
    auth: RequestContext,
) -> dict[str, Any]:
    """Attach trusted tenant/principal; reject conflicting client tenant_id."""
    merged = dict(client_context)
    client_tenant = merged.get("tenant_id")
    if client_tenant is not None and str(client_tenant) != auth.tenant.tenant_id:
        msg = "context.tenant_id must match authenticated tenant"
        raise ValueError(msg)
    merged["tenant_id"] = auth.tenant.tenant_id
    merged["principal_id"] = auth.principal.principal_id
    if "request_id" not in merged or not merged["request_id"]:
        merged["request_id"] = auth.request_id
    perms = merged.get("permissions_scope")
    if not isinstance(perms, dict):
        perms = {}
    else:
        perms = dict(perms)
    perms.setdefault("roles", [r.value for r in auth.principal.roles])
    merged["permissions_scope"] = perms
    return merged
