"""Fake provider returns schema-constrained structured outputs."""

from __future__ import annotations

from uuid import uuid4

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentValidationModelRequest,
)

from model_runtime.providers import FakeStructuredProvider
from model_runtime.service import ModelRuntimeService


def test_fake_analyze_structure() -> None:
    p = FakeStructuredProvider()
    out = p.analyze_incident(
        IncidentAnalysisModelRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            incident_id="inc-99",
            execution_input_excerpt={"severity": "high"},
        ),
    )
    assert "inc-99" in out.incident_summary
    assert len(out.possible_causes) == 3
    assert out.provider_label == "fake_structured_v1"
    assert out.model_invocation_id


def test_fake_validate_picks_from_prior_causes() -> None:
    p = FakeStructuredProvider()
    out = p.validate_incident(
        IncidentValidationModelRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            incident_id="inc-99",
            prior_possible_causes=["a", "b"],
            evidence_summary_excerpt="metrics spike",
        ),
    )
    assert out.likely_cause in ("a", "b")
    assert out.validation_status == "passed"
    assert 0.0 <= out.confidence_score <= 1.0
    assert out.digest


def test_service_defaults_to_fake() -> None:
    svc = ModelRuntimeService()
    out = svc.analyze_incident(
        IncidentAnalysisModelRequest(execution_id=uuid4(), step_id=uuid4(), incident_id="x"),
    )
    assert out.provider_label == "fake_structured_v1"


def test_unconfigured_http_raises() -> None:
    from model_runtime.providers import UnconfiguredHttpProvider

    u = UnconfiguredHttpProvider()
    try:
        u.analyze_incident(
            IncidentAnalysisModelRequest(execution_id=uuid4(), step_id=uuid4(), incident_id="y"),
        )
    except RuntimeError as e:
        assert "configure" in str(e).lower()
    else:
        raise AssertionError("expected RuntimeError")
