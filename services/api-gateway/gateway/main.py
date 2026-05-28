"""FastAPI application: mount `/v1` routers only."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from gateway.config import Settings, get_settings
from gateway.dependencies import build_gateway_state
from gateway.routers import (
    approvals,
    executions,
    feedback,
    insights,
    metrics,
    operational,
    policies,
    replay,
    trace,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = build_gateway_state(settings)
        app.state.gateway = state
        if settings.use_execution_worker_queue:
            import threading

            def _worker_loop() -> None:
                import time

                while True:
                    if not state.execution_worker.run_once():
                        time.sleep(0.05)

            thread = threading.Thread(target=_worker_loop, name="execution-worker", daemon=True)
            thread.start()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(executions.router, prefix="/v1")
    app.include_router(metrics.router, prefix="/v1")
    app.include_router(trace.router, prefix="/v1")
    app.include_router(approvals.router, prefix="/v1")
    app.include_router(feedback.router, prefix="/v1")
    app.include_router(replay.router, prefix="/v1")
    app.include_router(insights.router, prefix="/v1")
    app.include_router(policies.router, prefix="/v1")
    app.include_router(operational.router)
    return app


app = create_app()
