"""Bounded retries and observability around provider calls."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from common_schemas import (
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
    ModelInvocationTelemetry,
)

from model_runtime.config import ModelRuntimeConfig
from model_runtime.errors import SchemaValidationModelError, TransientModelError
from model_runtime.result import ReasoningCallResult

T = TypeVar("T")

try:
    from observability import emit_event, get_registry, observe_latency_ms
except ImportError:  # pragma: no cover - optional in minimal test paths

    def emit_event(_event_type: str, **_fields: Any) -> None:
        return None

    def observe_latency_ms(*_a: Any, **_k: Any) -> None:
        return None

    def get_registry() -> Any:
        class _Noop:
            def inc(self, *_a: Any, **_k: Any) -> None:
                return None

        return _Noop()


class ResilientStructuredProvider:
    """Wraps a provider with retries, latency, and structured operational events."""

    def __init__(self, inner: Any, config: ModelRuntimeConfig) -> None:
        self._inner = inner
        self._config = config

    def analyze_incident(
        self,
        request: IncidentAnalysisModelRequest,
    ) -> Any:
        return self._call_with_retries(
            "analyze_incident",
            request,
            lambda: self._inner.analyze_incident(request),
        )

    def validate_incident(
        self,
        request: IncidentValidationModelRequest,
    ) -> Any:
        return self._call_with_retries(
            "validate_incident",
            request,
            lambda: self._inner.validate_incident(request),
        )

    def _call_with_retries(
        self,
        task: str,
        request: IncidentAnalysisModelRequest | IncidentValidationModelRequest,
        fn: Callable[[], Any],
    ) -> Any:
        max_attempts = max(1, self._config.max_retries + 1)
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                emit_event(
                    "model_request",
                    task=task,
                    execution_id=str(request.execution_id),
                    step_id=str(request.step_id),
                    attempt=attempt,
                    provider_type=getattr(self._inner, "provider_type", "unknown"),
                )
                started = time.perf_counter()
                result = fn()
                latency_ms = int((time.perf_counter() - started) * 1000)
                telemetry: ModelInvocationTelemetry = result.telemetry
                updated = telemetry.model_copy(
                    update={"latency_ms": latency_ms, "retry_count": attempt},
                )
                result = ReasoningCallResult(
                    output=result.output.model_copy(update={"invocation": updated}),
                    telemetry=updated,
                )
                observe_latency_ms(
                    "model_request",
                    float(latency_ms),
                    labels={"provider": updated.provider_type or "unknown", "task": task},
                )
                get_registry().inc(
                    "model_requests_total",
                    labels={"provider": updated.provider_type or "unknown", "task": task},
                )
                emit_event(
                    "model_success",
                    task=task,
                    execution_id=str(request.execution_id),
                    step_id=str(request.step_id),
                    latency_ms=latency_ms,
                    retry_count=attempt,
                    total_tokens=updated.total_tokens,
                )
                return result
            except SchemaValidationModelError as exc:
                get_registry().inc(
                    "model_failures_total",
                    labels={"reason": "schema_validation", "task": task},
                )
                emit_event(
                    "model_schema_failure",
                    task=task,
                    execution_id=str(request.execution_id),
                    step_id=str(request.step_id),
                    error_class=type(exc).__name__,
                )
                raise
            except TransientModelError as exc:
                last_exc = exc
                get_registry().inc(
                    "model_retries_total",
                    labels={"task": task},
                )
                emit_event(
                    "model_retry",
                    task=task,
                    execution_id=str(request.execution_id),
                    step_id=str(request.step_id),
                    attempt=attempt,
                    error_class=type(exc).__name__,
                )
                if attempt + 1 >= max_attempts:
                    break
                time.sleep(self._config.retry_backoff_seconds * (attempt + 1))
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                get_registry().inc(
                    "model_failures_total",
                    labels={"reason": type(exc).__name__, "task": task},
                )
                emit_event(
                    "model_failure",
                    task=task,
                    execution_id=str(request.execution_id),
                    step_id=str(request.step_id),
                    error_class=type(exc).__name__,
                )
                raise

        get_registry().inc("model_failures_total", labels={"reason": "exhausted_retries", "task": task})
        if isinstance(last_exc, TransientModelError) and "timed out" in str(last_exc).lower():
            get_registry().inc("model_timeouts_total", labels={"task": task})
        emit_event(
            "model_failure",
            task=task,
            execution_id=str(request.execution_id),
            step_id=str(request.step_id),
            error_class=type(last_exc).__name__ if last_exc else "unknown",
            exhausted_retries=True,
        )
        assert last_exc is not None
        raise last_exc
