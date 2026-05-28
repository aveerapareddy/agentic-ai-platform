"""Operational metrics and runtime health (not business /v1 APIs)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from gateway.config import get_settings

router = APIRouter(tags=["operational"])


@router.get("/metrics", response_class=PlainTextResponse)
def operational_metrics() -> Response:
    try:
        from observability import render_prometheus

        body = render_prometheus()
    except ImportError:
        body = "# observability package not available\n"
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4")


@router.get("/health/runtime")
def runtime_health() -> dict[str, str]:
    settings = get_settings()
    provider = "unknown"
    try:
        from model_runtime.config import load_config_from_env

        provider = load_config_from_env().provider_type
    except Exception:
        provider = "unavailable"
    return {
        "status": "ok",
        "gateway": settings.app_name,
        "model_provider": provider,
    }
