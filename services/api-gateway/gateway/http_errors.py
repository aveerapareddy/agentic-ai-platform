"""Consistent error envelope (api-design §7 shape, simplified)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, Request


def api_error(
    *,
    code: str,
    message: str,
    status_code: int,
    request: Request | None = None,
) -> HTTPException:
    rid = None
    if request is not None:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    body: dict[str, Any] = {"error": {"code": code, "message": message, "request_id": rid}}
    return HTTPException(status_code=status_code, detail=body)
