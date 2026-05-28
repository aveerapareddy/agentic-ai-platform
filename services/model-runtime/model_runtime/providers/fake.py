"""Deterministic structured outputs; simulates bounded LLM JSON without network."""

from __future__ import annotations

import hashlib
import json
import time
from uuid import uuid4

from common_schemas import (
    CostAttributionAnalysisModelRequest,
    CostAttributionReasoningOutput,
    CostAttributionValidationModelRequest,
    CostValidationOutput,
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

    def analyze_cost_anomaly(
        self,
        request: CostAttributionAnalysisModelRequest,
    ) -> ReasoningCallResult[CostAttributionReasoningOutput]:
        started = time.perf_counter()
        payload = json.dumps({"scope_id": request.scope_id, "task": "analyze_cost"}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        inv = str(uuid4())
        latency_ms = int((time.perf_counter() - started) * 1000)
        telemetry = ModelInvocationTelemetry(
            latency_ms=latency_ms,
            retry_count=0,
            provider_type=self.provider_type,
            model_name="fake",
        )
        svc_suffix = request.scope_id[-4:] if len(request.scope_id) >= 4 else "svc"
        out = CostAttributionReasoningOutput(
            suspected_service=f"svc-{svc_suffix}",
            suspected_team="finops",
            anomaly_type="spend_spike",
            estimated_cost_impact_usd=round(120.0 + (int(digest[:4], 16) % 80), 2),
            attribution_summary=(
                f"[model:{_FAKE_PROVIDER_LABEL}] Scope {request.scope_id}: spend anomaly vs baseline "
                f"(digest {digest})"
            ),
            optimization_candidates=["rightsizing", "idle_resource_cleanup"],
            evidence_references=[f"cost-model:{digest}"],
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
            invocation=telemetry,
        )
        return ReasoningCallResult(output=out, telemetry=telemetry)

    def validate_cost_attribution(
        self,
        request: CostAttributionValidationModelRequest,
    ) -> ReasoningCallResult[CostValidationOutput]:
        started = time.perf_counter()
        payload = json.dumps(
            {"scope_id": request.scope_id, "prior": request.prior_attribution_summary},
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
        )
        conf = 0.88
        out = CostValidationOutput(
            validation_status="passed",
            confidence=conf,
            likely_service=f"svc-{request.scope_id[-4:]}" if len(request.scope_id) >= 4 else "svc-unknown",
            likely_team="finops",
            rationale_short="Fake provider: attribution consistent with billing and usage evidence.",
            recommended_actions=["review_reserved_capacity", "enable_cost_anomaly_alerts"],
            digest=digest,
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
            invocation=telemetry,
        )
        return ReasoningCallResult(output=out, telemetry=telemetry)
