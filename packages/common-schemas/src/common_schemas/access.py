"""Gateway auth and request context contracts (Session E — local/dev foundation)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    """Coarse RBAC roles for gateway enforcement."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    APPROVER = "approver"
    ADMIN = "admin"


class Principal(BaseModel):
    """Authenticated caller identity."""

    model_config = ConfigDict(extra="forbid")

    principal_id: str = Field(max_length=256)
    roles: list[Role] = Field(default_factory=list)
    display_name: str | None = Field(default=None, max_length=256)


class TenantContext(BaseModel):
    """Trusted tenant scope for a request."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(max_length=256)


class RequestContext(BaseModel):
    """Gateway-built context propagated to execution creation and policy simulation."""

    model_config = ConfigDict(extra="forbid")

    principal: Principal
    tenant: TenantContext
    request_id: str = Field(max_length=128)
    permissions_scope: dict[str, list[str]] = Field(default_factory=dict)

    def has_role(self, role: Role) -> bool:
        return role in self.principal.roles

    def has_any_role(self, *roles: Role) -> bool:
        return any(self.has_role(r) for r in roles)
