"""Delegate replay diff reads to orchestrator ReplayDiffService only."""

from __future__ import annotations

from uuid import UUID

from gateway._bootstrap import ensure_platform_paths

ensure_platform_paths()

from app.services.replay_diff_service import ReplayDiffNotFoundError, ReplayDiffService
from common_schemas import ReplayDiffSummary


class ReplayDiffFacade:
    def __init__(self, *, replay_diff_service: ReplayDiffService) -> None:
        self._svc = replay_diff_service

    def get_replay_diff(self, source_execution_id: UUID, replay_execution_id: UUID) -> ReplayDiffSummary:
        try:
            return self._svc.compare(source_execution_id, replay_execution_id)
        except ReplayDiffNotFoundError as e:
            raise KeyError(str(e)) from e
