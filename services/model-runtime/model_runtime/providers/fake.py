"""Deterministic structured outputs; simulates bounded LLM JSON without network."""

from __future__ import annotations

import hashlib
import json
import time
from uuid import uuid4

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
    ModelInvocationTelemetry,
)

from model_runtime.result import ReasoningCallResult

_FAKE_PROVIDER_LABEL = "fake_structured_v1"
_DEFAULT_CAUSES = ("config_drift", "dependency_failure", "capacity_saturation")


class FakeStructuredProvider:
    """Default provider for CI/local — no API keys required."""

    provider_type = "fake"

    def analyze_incident(
        self,
        request: IncidentAnalysisModelRequest,
    ) -> ReasoningCallResult[IncidentAnalysisReasoningOutput]:
        started = time.perf_counter()
        payload = json.dumps(
            {"incident_id": request.incident_id, "task": "analyze"},
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        inv = str(uuid4())
        latency_ms = int((time.perf_counter() - started) * 1000)
        telemetry = ModelInvocationTelemetry(
            latency_ms=latency_ms,
            retry_count=0,
            provider_type=self.provider_type,
            model_name="fake",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )
        out = IncidentAnalysisReasoningOutput(
            incident_summary=(
                f"[model:{_FAKE_PROVIDER_LABEL}] Incident {request.incident_id}: "
                f"elevated error rate and latency correlated (digest {digest})"
            ),
            possible_causes=list(_DEFAULT_CAUSES),
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
            invocation=telemetry,
        )
        return ReasoningCallResult(output=out, telemetry=telemetry)

    def validate_incident(
        self,
        request: IncidentValidationModelRequest,
    ) -> ReasoningCallResult[IncidentValidationReasoningOutput]:
        started = time.perf_counter()
        causes = list(request.prior_possible_causes) or list(_DEFAULT_CAUSES)
        payload = json.dumps({"incident_id": request.incident_id, "causes": causes}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        idx = int(digest[:2], 16) % len(causes)
        likely = causes[idx]
        inv = str(uuid4())
        latency_ms = int((time.perf_counter() - started) * 1000)
        telemetry = ModelInvocationTelemetry(
            latency_ms=latency_ms,
            retry_count=0,
            provider_type=self.provider_type,
            model_name="fake",
        )
        out = IncidentValidationReasoningOutput(
            likely_cause=likely,
            validation_status="passed",
            confidence_score=0.91,
            rationale_short="Fake provider: bounded consistency with prior causes list.",
            digest=digest,
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
            invocation=telemetry,
        )
        return ReasoningCallResult(output=out, telemetry=telemetry)
