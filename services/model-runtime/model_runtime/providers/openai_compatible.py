"""OpenAI-compatible chat completions → shared-schema structured outputs."""

from __future__ import annotations

import json
import time
from typing import Any, Callable
from uuid import uuid4

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
    ModelInvocationTelemetry,
)
from pydantic import ValidationError

from model_runtime.config import ModelRuntimeConfig
from model_runtime.errors import NonRetryableModelError, SchemaValidationModelError
from model_runtime.providers.http_common import post_json
from model_runtime.result import ReasoningCallResult

PostFn = Callable[..., dict[str, Any]]


class OpenAICompatibleProvider:
    """Single-attempt HTTP provider; retries are applied by ResilientStructuredProvider."""

    provider_type = "openai"

    def __init__(
        self,
        config: ModelRuntimeConfig,
        *,
        post_fn: PostFn | None = None,
    ) -> None:
        if not config.api_key:
            raise NonRetryableModelError("MODEL_API_KEY or OPENAI_API_KEY is required for openai provider")
        if not config.base_url:
            raise NonRetryableModelError("MODEL_BASE_URL is required for openai provider")
        self._config = config
        self._post = post_fn or post_json

    def analyze_incident(
        self,
        request: IncidentAnalysisModelRequest,
    ) -> ReasoningCallResult[IncidentAnalysisReasoningOutput]:
        schema_hint = {
            "incident_summary": "string",
            "possible_causes": ["string"],
        }
        user = {
            "task": "analyze_incident",
            "incident_id": request.incident_id,
            "workflow_type": request.workflow_type,
            "execution_input_excerpt": request.execution_input_excerpt,
        }
        return self._invoke(
            task="analyze_incident",
            user_payload=user,
            schema_hint=schema_hint,
            build_output=self._parse_analyze,
            request_ids=(request.execution_id, request.step_id),
        )

    def validate_incident(
        self,
        request: IncidentValidationModelRequest,
    ) -> ReasoningCallResult[IncidentValidationReasoningOutput]:
        schema_hint = {
            "likely_cause": "string",
            "validation_status": "string",
            "confidence_score": 0.0,
            "rationale_short": "string",
            "digest": "string",
        }
        user = {
            "task": "validate_incident",
            "incident_id": request.incident_id,
            "prior_possible_causes": request.prior_possible_causes,
            "prior_incident_summary_excerpt": request.prior_incident_summary_excerpt,
            "evidence_summary_excerpt": request.evidence_summary_excerpt,
        }
        return self._invoke(
            task="validate_incident",
            user_payload=user,
            schema_hint=schema_hint,
            build_output=self._parse_validate,
            request_ids=(request.execution_id, request.step_id),
        )

    def _invoke(
        self,
        *,
        task: str,
        user_payload: dict[str, Any],
        schema_hint: dict[str, Any],
        build_output: Callable[[dict[str, Any], str, str, ModelInvocationTelemetry], Any],
        request_ids: tuple[Any, Any],
    ) -> ReasoningCallResult[Any]:
        started = time.perf_counter()
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._config.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return a single JSON object only. Fields must match this schema hint: "
                        + json.dumps(schema_hint)
                    ),
                },
                {"role": "user", "content": json.dumps(user_payload, sort_keys=True)},
            ],
            "temperature": 0,
        }
        resp = self._post(url, headers=headers, body=body, timeout_seconds=self._config.timeout_seconds)
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = resp.get("usage") if isinstance(resp.get("usage"), dict) else {}
        telemetry = ModelInvocationTelemetry(
            latency_ms=latency_ms,
            retry_count=0,
            provider_type=self.provider_type,
            model_name=self._config.model_name,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )
        content = _extract_message_content(resp)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SchemaValidationModelError(f"provider JSON parse failed: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SchemaValidationModelError("provider response must be a JSON object")
        inv_id = str(uuid4())
        label = f"openai:{self._config.model_name}"
        out = build_output(parsed, inv_id, label, telemetry)
        return ReasoningCallResult(output=out, telemetry=telemetry)

    def _parse_analyze(
        self,
        parsed: dict[str, Any],
        inv_id: str,
        label: str,
        telemetry: ModelInvocationTelemetry,
    ) -> IncidentAnalysisReasoningOutput:
        causes_raw = parsed.get("possible_causes")
        causes = [str(x) for x in causes_raw] if isinstance(causes_raw, list) else []
        try:
            return IncidentAnalysisReasoningOutput(
                incident_summary=str(parsed.get("incident_summary", ""))[:4000],
                possible_causes=causes[:16],
                model_invocation_id=inv_id,
                provider_label=label,
                invocation=telemetry,
            )
        except ValidationError as exc:
            raise SchemaValidationModelError(str(exc)) from exc

    def _parse_validate(
        self,
        parsed: dict[str, Any],
        inv_id: str,
        label: str,
        telemetry: ModelInvocationTelemetry,
    ) -> IncidentValidationReasoningOutput:
        try:
            return IncidentValidationReasoningOutput(
                likely_cause=str(parsed.get("likely_cause", ""))[:128],
                validation_status=str(parsed.get("validation_status", ""))[:32],
                confidence_score=float(parsed.get("confidence_score", 0.0)),
                rationale_short=str(parsed.get("rationale_short", ""))[:500],
                digest=str(parsed.get("digest", ""))[:64],
                model_invocation_id=inv_id,
                provider_label=label,
                invocation=telemetry,
            )
        except ValidationError as exc:
            raise SchemaValidationModelError(str(exc)) from exc


class AzureOpenAICompatibleProvider(OpenAICompatibleProvider):
    """Azure OpenAI: deployment URL and api-key header."""

    provider_type = "azure_openai"

    def __init__(self, config: ModelRuntimeConfig, *, post_fn: PostFn | None = None) -> None:
        if not config.api_key:
            raise NonRetryableModelError("AZURE_OPENAI_API_KEY is required for azure_openai provider")
        if not config.base_url:
            raise NonRetryableModelError("AZURE_OPENAI_ENDPOINT is required for azure_openai provider")
        if not config.azure_deployment:
            raise NonRetryableModelError("AZURE_OPENAI_DEPLOYMENT is required for azure_openai provider")
        super().__init__(config, post_fn=post_fn)
        self.provider_type = "azure_openai"

    def _chat_url(self) -> str:
        deployment = self._config.azure_deployment
        version = self._config.azure_api_version
        base = self._config.base_url.rstrip("/")
        return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={version}"

    def _auth_headers(self) -> dict[str, str]:
        return {
            "api-key": self._config.api_key or "",
            "Content-Type": "application/json",
        }

    def _invoke(
        self,
        *,
        task: str,
        user_payload: dict[str, Any],
        schema_hint: dict[str, Any],
        build_output: Callable[[dict[str, Any], str, str, ModelInvocationTelemetry], Any],
        request_ids: tuple[Any, Any],
    ) -> ReasoningCallResult[Any]:
        started = time.perf_counter()
        body = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return a single JSON object only. Fields must match: "
                        + json.dumps(schema_hint)
                    ),
                },
                {"role": "user", "content": json.dumps(user_payload, sort_keys=True)},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        resp = self._post(
            self._chat_url(),
            headers=self._auth_headers(),
            body=body,
            timeout_seconds=self._config.timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = resp.get("usage") if isinstance(resp.get("usage"), dict) else {}
        model_name = self._config.azure_deployment or self._config.model_name
        telemetry = ModelInvocationTelemetry(
            latency_ms=latency_ms,
            retry_count=0,
            provider_type=self.provider_type,
            model_name=model_name,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )
        content = _extract_message_content(resp)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SchemaValidationModelError(f"provider JSON parse failed: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SchemaValidationModelError("provider response must be a JSON object")
        inv_id = str(uuid4())
        label = f"azure_openai:{model_name}"
        out = build_output(parsed, inv_id, label, telemetry)
        return ReasoningCallResult(output=out, telemetry=telemetry)


def _extract_message_content(resp: dict[str, Any]) -> str:
    choices = resp.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SchemaValidationModelError("missing choices in provider response")
    first = choices[0]
    if not isinstance(first, dict):
        raise SchemaValidationModelError("invalid choice shape")
    message = first.get("message")
    if not isinstance(message, dict):
        raise SchemaValidationModelError("missing message in choice")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise SchemaValidationModelError("empty message content")
    return content
