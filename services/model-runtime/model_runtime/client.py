"""Abstraction for providers that return schema-validated reasoning outputs only."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
)


@runtime_checkable
class StructuredReasoningClient(Protocol):
    """Provider boundary: no raw completion strings cross the orchestrator."""

    def analyze_incident(self, request: IncidentAnalysisModelRequest) -> IncidentAnalysisReasoningOutput:
        """Return validated analysis; implementations must not mutate execution state."""

    def validate_incident(self, request: IncidentValidationModelRequest) -> IncidentValidationReasoningOutput:
        """Return validated validation verdict; advisory only until validators record outcome."""
