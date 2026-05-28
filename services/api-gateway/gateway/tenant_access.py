"""Tenant-scoped access helpers for execution reads."""

from __future__ import annotations

from uuid import UUID

from common_schemas import Execution, RequestContext
from fastapi import Request

from gateway._bootstrap import ensure_platform_paths
from gateway.http_errors import api_error

ensure_platform_paths()

from app.adapters.repository import Repository


def assert_execution_visible(
    repo: Repository,
    execution_id: UUID,
    auth: RequestContext,
    *,
    request: Request | None = None,
) -> Execution:
    ex = repo.get_execution(execution_id)
    if ex is None:
        raise api_error(
            code="NOT_FOUND",
            message="execution not found",
            status_code=404,
            request=request,
        )
    ctx = repo.get_context(ex.execution_context_id)
    if ctx is None or ctx.tenant_id != auth.tenant.tenant_id:
        raise api_error(
            code="FORBIDDEN",
            message="execution not visible for tenant",
            status_code=403,
            request=request,
        )
    return ex
