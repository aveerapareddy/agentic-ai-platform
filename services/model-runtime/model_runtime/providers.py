"""Provider implementations: deterministic fake for CI/local; optional real hook later."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
)

_FAKE_PROVIDER_LABEL = "fake_structured_v1"
_DEFAULT_CAUSES = ("config_drift", "dependency_failure", "capacity_saturation")


class FakeStructuredProvider:
    """Deterministic structured outputs; simulates bounded LLM JSON without network."""

    def analyze_incident(self, request: IncidentAnalysisModelRequest) -> IncidentAnalysisReasoningOutput:
        payload = json.dumps(
            {"incident_id": request.incident_id, "task": "analyze"},
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        inv = str(uuid4())
        return IncidentAnalysisReasoningOutput(
            incident_summary=(
                f"[model:{_FAKE_PROVIDER_LABEL}] Incident {request.incident_id}: "
                f"elevated error rate and latency correlated (digest {digest})"
            ),
            possible_causes=list(_DEFAULT_CAUSES),
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
        )

    def validate_incident(self, request: IncidentValidationModelRequest) -> IncidentValidationReasoningOutput:
        causes = list(request.prior_possible_causes) or list(_DEFAULT_CAUSES)
        payload = json.dumps({"incident_id": request.incident_id, "causes": causes}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        idx = int(digest[:2], 16) % len(causes)
        likely = causes[idx]
        inv = str(uuid4())
        return IncidentValidationReasoningOutput(
            likely_cause=likely,
            validation_status="passed",
            confidence_score=0.91,
            rationale_short="Fake provider: bounded consistency with prior causes list.",
            digest=digest,
            model_invocation_id=inv,
            provider_label=_FAKE_PROVIDER_LABEL,
        )


class UnconfiguredHttpProvider:
    """Placeholder for a future HTTP/chat provider; not wired in Phase 5."""

    def analyze_incident(self, request: IncidentAnalysisModelRequest) -> IncidentAnalysisReasoningOutput:
        raise RuntimeError(
            "UnconfiguredHttpProvider: configure credentials and wire parsing before use.",
        )

    def validate_incident(self, request: IncidentValidationModelRequest) -> IncidentValidationReasoningOutput:
        raise RuntimeError(
            "UnconfiguredHttpProvider: configure credentials and wire parsing before use.",
        )
