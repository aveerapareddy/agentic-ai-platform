"""Gateway response models for Mukti v2 insights — mirror common_schemas (advisory only)."""

from __future__ import annotations

from common_schemas import (
    CrossExecutionInsight,
    MuktiInsightsSummary,
    RankedImprovementSuggestion,
)

MuktiInsightsSummaryResponse = MuktiInsightsSummary
CrossExecutionInsightResponse = CrossExecutionInsight
RankedImprovementSuggestionResponse = RankedImprovementSuggestion
