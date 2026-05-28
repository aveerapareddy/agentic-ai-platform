from __future__ import annotations

import json
from uuid import uuid4

from common_schemas import IncidentAnalysisModelRequest

from model_runtime.config import ModelRuntimeConfig
from model_runtime.providers.openai_compatible import OpenAICompatibleProvider


def test_openai_provider_parses_structured_json() -> None:
    def fake_post(url: str, *, headers: dict, body: dict, timeout_seconds: float) -> dict:
        payload = {
            "incident_summary": "Elevated errors on checkout",
            "possible_causes": ["dependency_failure"],
        }
        return {
            "choices": [{"message": {"content": json.dumps(payload)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    cfg = ModelRuntimeConfig(
        provider_type="openai",
        api_key="test-key",
        base_url="https://example.test/v1",
        model_name="gpt-test",
        timeout_seconds=5.0,
        max_retries=0,
    )
    provider = OpenAICompatibleProvider(cfg, post_fn=fake_post)
    result = provider.analyze_incident(
        IncidentAnalysisModelRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            incident_id="inc-1",
            execution_input_excerpt={"severity": "high"},
        ),
    )
    assert "checkout" in result.output.incident_summary
    assert result.telemetry.total_tokens == 30
    assert result.telemetry.input_tokens == 10
