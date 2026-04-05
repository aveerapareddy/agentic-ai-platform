"""Mukti facade: analyze frozen snapshots only."""

from __future__ import annotations

from datetime import datetime, timezone

from common_schemas import ExecutionFeedback, MuktiAnalysisInput

from mukti_agent.analyzer import MuktiAnalyzer


class MuktiService:
    """Does not persist or call orchestrator; callers store ExecutionFeedback via feedback-service."""

    def __init__(self, analyzer: MuktiAnalyzer | None = None) -> None:
        self._analyzer = analyzer or MuktiAnalyzer()

    def analyze(self, inp: MuktiAnalysisInput, *, now: datetime | None = None) -> ExecutionFeedback:
        ts = now or datetime.now(timezone.utc)
        return self._analyzer.analyze(inp, now=ts)
