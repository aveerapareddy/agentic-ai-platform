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
from gateway.services.mukti_facade import MuktiFacade
from gateway.services.replay_diff_facade import ReplayDiffFacade

ensure_platform_paths()

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService
from app.services.replay_diff_service import ReplayDiffService
from app.runtime.queue import InMemoryExecutionQueue
from app.runtime.worker import ExecutionWorker
from app.services.replay_service import ReplayService
from evaluation_engine import EvaluationService
from feedback_service.service import FeedbackService
from mukti_agent.service import MuktiService


@dataclass
class GatewayState:
    settings: Settings
    repository: InMemoryRepository
    execution_queue: InMemoryExecutionQueue
    execution_service: ExecutionService
    execution_worker: ExecutionWorker
    feedback_service: FeedbackService
    evaluation_service: EvaluationService
    mukti_service: MuktiService
    replay_service: ReplayService
    replay_diff_service: ReplayDiffService
    idempotency: dict[tuple[str, str, str], UUID] = field(default_factory=dict)


def build_gateway_state(settings: Settings | None = None) -> GatewayState:
    settings = settings or get_settings()
    repo = InMemoryRepository()
    queue = InMemoryExecutionQueue()
    execution_service = ExecutionService(repo, queue=queue)
    worker = ExecutionWorker(execution_service, queue)
    feedback_service = FeedbackService()
    evaluation_service = EvaluationService(repo)
    mukti_service = MuktiService()
    replay_service = ReplayService(repo, execution_service)
    replay_diff_service = ReplayDiffService(repo)
    return GatewayState(
        settings=settings,
        repository=repo,
        execution_queue=queue,
        execution_service=execution_service,
        execution_worker=worker,
        feedback_service=feedback_service,
        evaluation_service=evaluation_service,
        mukti_service=mukti_service,
        replay_service=replay_service,
        replay_diff_service=replay_diff_service,
    )


def get_state(request: Request) -> GatewayState:
    return request.app.state.gateway


def get_execution_facade(state: Annotated[GatewayState, Depends(get_state)]) -> ExecutionFacade:
    return ExecutionFacade(
        execution_service=state.execution_service,
        repository=state.repository,
        idempotency_store=state.idempotency,
        settings=state.settings,
        replay_service=state.replay_service,
    )


def get_feedback_facade(state: Annotated[GatewayState, Depends(get_state)]) -> FeedbackFacade:
    return FeedbackFacade(feedback_service=state.feedback_service)


def get_evaluation_facade(state: Annotated[GatewayState, Depends(get_state)]) -> EvaluationFacade:
    return EvaluationFacade(evaluation_service=state.evaluation_service)


def get_mukti_facade(state: Annotated[GatewayState, Depends(get_state)]) -> MuktiFacade:
    return MuktiFacade(
        mukti_service=state.mukti_service,
        feedback_service=state.feedback_service,
        execution_service=state.execution_service,
    )


async def auth_placeholder(request: Request) -> None:
    """Reserved for JWT / mTLS; no-op in default Phase 8 deployment."""
    _ = request


ExecutionFacadeDep = Annotated[ExecutionFacade, Depends(get_execution_facade)]
FeedbackFacadeDep = Annotated[FeedbackFacade, Depends(get_feedback_facade)]
EvaluationFacadeDep = Annotated[EvaluationFacade, Depends(get_evaluation_facade)]
MuktiFacadeDep = Annotated[MuktiFacade, Depends(get_mukti_facade)]


def get_replay_diff_facade(state: Annotated[GatewayState, Depends(get_state)]) -> ReplayDiffFacade:
    return ReplayDiffFacade(replay_diff_service=state.replay_diff_service)


ReplayDiffFacadeDep = Annotated[ReplayDiffFacade, Depends(get_replay_diff_facade)]
