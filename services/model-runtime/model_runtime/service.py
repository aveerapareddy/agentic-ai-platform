"""Facade: injectable client; default fake provider requires no API keys."""

from __future__ import annotations

from common_schemas import (
    CostAttributionAnalysisModelRequest,
    CostAttributionValidationModelRequest,
    IncidentAnalysisModelRequest,
    IncidentValidationModelRequest,
)

from model_runtime.config import ModelRuntimeConfig, load_config_from_env
from model_runtime.providers.factory import build_provider
from model_runtime.resilient import ResilientStructuredProvider
from model_runtime.result import ReasoningCallResult


class ModelRuntimeService:
    """Owns bounded model calls only; orchestrator coordinates when steps run."""

    def __init__(
        self,
        client: object | None = None,
        *,
        config: ModelRuntimeConfig | None = None,
    ) -> None:
        cfg = config or load_config_from_env()
        inner = client or build_provider(cfg)
        self._client = (
            inner if isinstance(inner, ResilientStructuredProvider) else ResilientStructuredProvider(inner, cfg)
        )
        self._config = cfg

    @property
    def config(self) -> ModelRuntimeConfig:
        return self._config

    def analyze_incident(
        self,
        request: IncidentAnalysisModelRequest,
    ) -> ReasoningCallResult:
        return self._client.analyze_incident(request)

    def validate_incident(
        self,
        request: IncidentValidationModelRequest,
    ) -> ReasoningCallResult:
        return self._client.validate_incident(request)

    def analyze_cost_anomaly(
        self,
        request: CostAttributionAnalysisModelRequest,
    ) -> ReasoningCallResult:
        return self._client.analyze_cost_anomaly(request)

    def validate_cost_attribution(
        self,
        request: CostAttributionValidationModelRequest,
    ) -> ReasoningCallResult:
        return self._client.validate_cost_attribution(request)
