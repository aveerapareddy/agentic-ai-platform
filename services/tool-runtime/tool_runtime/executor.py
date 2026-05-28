"""Execute invoke requests with retries, timeouts, and structured ToolCall records."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Any
from uuid import uuid4

from common_schemas import (
    ToolCall,
    ToolCallId,
    ToolCallStatus,
    ToolIdempotency,
    ToolInvokeRequest,
    ToolSideEffectClass,
)
from urllib.error import HTTPError, URLError

from tool_runtime.errors import ToolCancelledError, ToolValidationError, TransientToolError
from tool_runtime.registry import ToolRegistry

CancelCheck = Callable[[], bool]


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, TransientToolError):
        return True
    if isinstance(exc, (TimeoutError, FuturesTimeoutError, ConnectionError, URLError, HTTPError)):
        return True
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in {110, 111}:
        return True
    return False


class ToolExecutor:
    """Validates registration, runs handler with bounded retries, returns ToolCall audit row."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        cancel_check: CancelCheck | None = None,
    ) -> None:
        self._registry = registry
        self._cancel_check = cancel_check

    def execute(self, request: ToolInvokeRequest, *, now: datetime) -> ToolCall:
        tcid: ToolCallId = uuid4()
        if request.policy_denied:
            return self._build_call(
                tcid,
                request,
                now=now,
                meta=None,
                side_effect_class=ToolSideEffectClass.STATE_CHANGING,
                idempotency=ToolIdempotency.NON_IDEMPOTENT,
                status=ToolCallStatus.REJECTED_BY_POLICY,
                output=None,
                latency_ms=0,
                error={"code": "rejected_by_policy", "message": "policy denied before tool invoke"},
                retry_count=0,
            )

        entry = self._registry.get(request.tool_name)
        if entry is None:
            return self._build_call(
                tcid,
                request,
                now=now,
                meta=None,
                side_effect_class=ToolSideEffectClass.READ_ONLY,
                idempotency=ToolIdempotency.IDEMPOTENT,
                status=ToolCallStatus.FAILURE,
                output=None,
                latency_ms=0,
                error={"code": "unknown_tool", "message": f"tool not registered: {request.tool_name}"},
                retry_count=0,
            )

        meta, handler = entry
        if self._is_cancelled():
            return self._build_call(
                tcid,
                request,
                now=now,
                meta=meta,
                side_effect_class=meta.side_effect_class,
                idempotency=meta.idempotency,
                status=ToolCallStatus.FAILURE,
                output=None,
                latency_ms=0,
                error={"code": "cancelled", "message": "execution cancellation requested"},
                retry_count=0,
            )

        try:
            self._validate_input(request)
        except ToolValidationError as exc:
            return self._build_call(
                tcid,
                request,
                now=now,
                meta=meta,
                side_effect_class=meta.side_effect_class,
                idempotency=meta.idempotency,
                status=ToolCallStatus.FAILURE,
                output=None,
                latency_ms=0,
                error={"code": "validation_error", "message": str(exc)},
                retry_count=0,
            )

        max_attempts = meta.retry_policy.max_retries + 1
        last_exc: Exception | None = None
        started = time.perf_counter_ns()
        for attempt in range(max_attempts):
            if self._is_cancelled():
                return self._build_call(
                    tcid,
                    request,
                    now=now,
                    meta=meta,
                    side_effect_class=meta.side_effect_class,
                    idempotency=meta.idempotency,
                    status=ToolCallStatus.FAILURE,
                    output=None,
                    latency_ms=self._elapsed_ms(started),
                    error={"code": "cancelled", "message": "execution cancellation requested"},
                    retry_count=attempt,
                )
            try:
                out = self._run_with_timeout(handler, request.input, timeout_ms=meta.timeout_bounds_ms)
                if not isinstance(out, dict):
                    raise ToolValidationError("tool handler must return dict")
                latency_ms = self._elapsed_ms(started)
                runtime_meta = {
                    "provider_id": meta.provider_id,
                    "retry_count": attempt,
                    "timed_out": False,
                }
                out = {**out, "_tool_runtime": runtime_meta}
                return self._build_call(
                    tcid,
                    request,
                    now=now,
                    meta=meta,
                    side_effect_class=meta.side_effect_class,
                    idempotency=meta.idempotency,
                    status=ToolCallStatus.SUCCESS,
                    output=out,
                    latency_ms=latency_ms,
                    error=None,
                    retry_count=attempt,
                )
            except ToolValidationError as exc:
                return self._build_call(
                    tcid,
                    request,
                    now=now,
                    meta=meta,
                    side_effect_class=meta.side_effect_class,
                    idempotency=meta.idempotency,
                    status=ToolCallStatus.FAILURE,
                    output=None,
                    latency_ms=self._elapsed_ms(started),
                    error={"code": "validation_error", "message": str(exc), "retry_count": attempt},
                    retry_count=attempt,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not _is_transient(exc) or attempt + 1 >= max_attempts:
                    break
                time.sleep(meta.retry_policy.backoff_ms * (attempt + 1) / 1000.0)

        latency_ms = self._elapsed_ms(started)
        timed_out = isinstance(last_exc, (TimeoutError, FuturesTimeoutError))
        status = ToolCallStatus.TIMEOUT if timed_out else ToolCallStatus.FAILURE
        code = "timeout" if timed_out else "tool_execution_error"
        return self._build_call(
            tcid,
            request,
            now=now,
            meta=meta,
            side_effect_class=meta.side_effect_class,
            idempotency=meta.idempotency,
            status=status,
            output=None,
            latency_ms=latency_ms,
            error={
                "code": code,
                "message": str(last_exc) if last_exc else "unknown",
                "retry_count": max_attempts - 1,
                "provider_id": meta.provider_id,
            },
            retry_count=max_attempts - 1,
        )

    def _validate_input(self, request: ToolInvokeRequest) -> None:
        if "incident_id" not in request.input and "id" not in request.input:
            raise ToolValidationError("incident_id or id is required in tool input")

    def _is_cancelled(self) -> bool:
        return bool(self._cancel_check and self._cancel_check())

    @staticmethod
    def _elapsed_ms(started_ns: int) -> int:
        return max(0, (time.perf_counter_ns() - started_ns) // 1_000_000)

    @staticmethod
    def _run_with_timeout(handler: Callable[[dict[str, Any]], dict[str, Any]], payload: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
        timeout_s = max(0.001, timeout_ms / 1000.0)
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(handler, dict(payload))
            try:
                return fut.result(timeout=timeout_s)
            except FuturesTimeoutError as exc:
                raise TimeoutError(f"tool exceeded timeout_bounds_ms={timeout_ms}") from exc

    @staticmethod
    def _build_call(
        tcid: ToolCallId,
        request: ToolInvokeRequest,
        *,
        now: datetime,
        meta: Any,
        side_effect_class: ToolSideEffectClass,
        idempotency: ToolIdempotency,
        status: ToolCallStatus,
        output: dict[str, Any] | None,
        latency_ms: int,
        error: dict[str, Any] | None,
        retry_count: int,
    ) -> ToolCall:
        _ = meta
        return ToolCall(
            tool_call_id=tcid,
            execution_id=request.execution_id,
            step_id=request.step_id,
            execution_context_id=request.execution_context_id,
            action_proposal_id=request.action_proposal_id,
            tool_name=request.tool_name,
            side_effect_class=side_effect_class,
            idempotency=idempotency,
            input=dict(request.input),
            output=output,
            status=status,
            latency_ms=latency_ms,
            error=error,
            created_at=now,
            updated_at=now,
        )
