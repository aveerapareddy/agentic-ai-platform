"""FastAPI application: mount `/v1` routers only."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from gateway.config import Settings, get_settings
from gateway.dependencies import build_gateway_state
from gateway.routers import approvals, executions, feedback, insights, metrics, replay, trace


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.gateway = build_gateway_state(settings)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(executions.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(trace.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(feedback.router, prefix="/v1")
    app.include_router(replay.router, prefix="/v1")
    app.include_router(insights.router, prefix="/v1")
    return app


app = create_app()
