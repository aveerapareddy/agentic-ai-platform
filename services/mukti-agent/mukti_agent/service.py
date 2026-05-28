"""Mukti facade: analyze frozen snapshots only."""

from __future__ import annotations

from datetime import datetime, timezone

from common_schemas import ExecutionFeedback, MuktiAnalysisInput, MuktiCrossExecutionInput, MuktiInsightsSummary

from mukti_agent.analyzer import MuktiAnalyzer
from mukti_agent.cross_execution import CrossExecutionAnalyzer


class MuktiService:
    """Does not persist or call orchestrator; callers store ExecutionFeedback via feedback-service."""

    def __init__(
        self,
        analyzer: MuktiAnalyzer | None = None,
        cross_analyzer: CrossExecutionAnalyzer | None = None,
    ) -> None:
        self._analyzer = analyzer or MuktiAnalyzer()
        self._cross = cross_analyzer or CrossExecutionAnalyzer()

    def analyze(self, inp: MuktiAnalysisInput, *, now: datetime | None = None) -> ExecutionFeedback:
        ts = now or datetime.now(timezone.utc)
        return self._analyzer.analyze(inp, now=ts)

    def analyze_cross_execution(self, inp: MuktiCrossExecutionInput) -> MuktiInsightsSummary:
        """Mukti v2 advisory rollup; no live execution or orchestrator calls."""
        return self._cross.analyze(inp)
