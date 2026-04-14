"""Shared FastAPI dependencies and process-wide gateway state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from gateway._bootstrap import ensure_platform_paths
from gateway.config import Settings, get_settings
from gateway.services.evaluation_facade import EvaluationFacade
from gateway.services.execution_facade import ExecutionFacade
from gateway.services.feedback_facade import FeedbackFacade

ensure_platform_paths()

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService
from evaluation_engine import EvaluationService
from feedback_service.service import FeedbackService


@dataclass
class GatewayState:
    settings: Settings
    repository: InMemoryRepository
    execution_service: ExecutionService
    feedback_service: FeedbackService
    evaluation_service: EvaluationService
    idempotency: dict[tuple[str, str, str], UUID] = field(default_factory=dict)


def build_gateway_state(settings: Settings | None = None) -> GatewayState:
    settings = settings or get_settings()
    repo = InMemoryRepository()
    execution_service = ExecutionService(repo)
    feedback_service = FeedbackService()
    evaluation_service = EvaluationService(repo)
    return GatewayState(
        settings=settings,
        repository=repo,
        execution_service=execution_service,
        feedback_service=feedback_service,
        evaluation_service=evaluation_service,
    )


def get_state(request: Request) -> GatewayState:
    return request.app.state.gateway


def get_execution_facade(state: Annotated[GatewayState, Depends(get_state)]) -> ExecutionFacade:
    return ExecutionFacade(
        execution_service=state.execution_service,
        repository=state.repository,
        idempotency_store=state.idempotency,
        settings=state.settings,
    )


def get_feedback_facade(state: Annotated[GatewayState, Depends(get_state)]) -> FeedbackFacade:
    return FeedbackFacade(feedback_service=state.feedback_service)


def get_evaluation_facade(state: Annotated[GatewayState, Depends(get_state)]) -> EvaluationFacade:
    return EvaluationFacade(evaluation_service=state.evaluation_service)


async def auth_placeholder(request: Request) -> None:
    """Reserved for JWT / mTLS; no-op in default Phase 8 deployment."""
    _ = request


ExecutionFacadeDep = Annotated[ExecutionFacade, Depends(get_execution_facade)]
FeedbackFacadeDep = Annotated[FeedbackFacade, Depends(get_feedback_facade)]
EvaluationFacadeDep = Annotated[EvaluationFacade, Depends(get_evaluation_facade)]
