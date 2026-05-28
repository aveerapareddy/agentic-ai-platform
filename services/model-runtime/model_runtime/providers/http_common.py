"""Shared HTTP helpers for OpenAI-compatible chat completions (stdlib only)."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Callable

from model_runtime.errors import NonRetryableModelError, TransientModelError, classify_http_status

PostJsonFn = Callable[..., dict[str, Any]]


def post_json(
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = _read_http_error_body(exc)
        err_cls = classify_http_status(exc.code)
        raise err_cls(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            raise TransientModelError("request timed out") from exc
        raise TransientModelError(str(reason)) from exc
    except TimeoutError as exc:
        raise TransientModelError("request timed out") from exc
    except json.JSONDecodeError as exc:
        raise NonRetryableModelError("invalid JSON response") from exc


def _read_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:500]
    except OSError:
        return str(exc.reason)
