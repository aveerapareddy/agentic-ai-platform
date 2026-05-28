from __future__ import annotations

from uuid import uuid4

import pytest
from common_schemas import IncidentAnalysisModelRequest
from observability.metrics import MetricsRegistry

from model_runtime.config import ModelRuntimeConfig
from model_runtime.errors import SchemaValidationModelError, TransientModelError
from model_runtime.providers.fake import FakeStructuredProvider
from model_runtime.resilient import ResilientStructuredProvider


def test_retries_transient_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class Flaky(FakeStructuredProvider):
        def analyze_incident(self, request):  # noqa: ANN001
            calls["n"] += 1
            if calls["n"] == 1:
                raise TransientModelError("timeout")
            return super().analyze_incident(request)

    cfg = ModelRuntimeConfig(max_retries=2, retry_backoff_seconds=0.0)
    client = ResilientStructuredProvider(Flaky(), cfg)
    req = IncidentAnalysisModelRequest(execution_id=uuid4(), step_id=uuid4(), incident_id="x")
    result = client.analyze_incident(req)
    assert result.output.incident_summary
    assert result.telemetry.retry_count == 1


def test_schema_validation_not_retried() -> None:
    class BadSchema(FakeStructuredProvider):
        def analyze_incident(self, request):  # noqa: ANN001
            raise SchemaValidationModelError("invalid shape")

    cfg = ModelRuntimeConfig(max_retries=3, retry_backoff_seconds=0.0)
    client = ResilientStructuredProvider(BadSchema(), cfg)
    req = IncidentAnalysisModelRequest(execution_id=uuid4(), step_id=uuid4(), incident_id="x")
    with pytest.raises(SchemaValidationModelError):
        client.analyze_incident(req)


def test_metrics_increment_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reg = MetricsRegistry()
    monkeypatch.setattr("observability.metrics._global", reg)
    cfg = ModelRuntimeConfig(max_retries=0, retry_backoff_seconds=0.0)
    client = ResilientStructuredProvider(FakeStructuredProvider(), cfg)
    req = IncidentAnalysisModelRequest(execution_id=uuid4(), step_id=uuid4(), incident_id="m")
    client.analyze_incident(req)
    snap = reg.snapshot()
    assert any(k[0] == "model_requests_total" for k in snap["counters"])
