"""Facade: injectable client; default fake provider requires no API keys."""

from __future__ import annotations

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
)

from model_runtime.client import StructuredReasoningClient
from model_runtime.providers import FakeStructuredProvider


class ModelRuntimeService:
    """Owns model calls only; orchestrator coordinates when steps run (constitution §8.2, §8.4)."""

    def __init__(self, client: StructuredReasoningClient | None = None) -> None:
        self._client: StructuredReasoningClient = client or FakeStructuredProvider()

    def analyze_incident(self, request: IncidentAnalysisModelRequest) -> IncidentAnalysisReasoningOutput:
        return self._client.analyze_incident(request)

    def validate_incident(self, request: IncidentValidationModelRequest) -> IncidentValidationReasoningOutput:
        return self._client.validate_incident(request)
