"""Model-runtime error taxonomy for retry classification."""

from __future__ import annotations


class ModelRuntimeError(Exception):
    """Base model-runtime failure."""


class TransientModelError(ModelRuntimeError):
    """Retryable: timeout, rate limit, network, upstream 5xx."""


class SchemaValidationModelError(ModelRuntimeError):
    """Non-retryable: provider returned JSON that failed schema validation."""


class NonRetryableModelError(ModelRuntimeError):
    """Non-retryable: invalid request, auth, or permanent provider error."""


def classify_http_status(status: int) -> type[ModelRuntimeError]:
    if status in (408, 429) or status >= 500:
        return TransientModelError
    if status in (400, 401, 403, 404, 422):
        return NonRetryableModelError
    return TransientModelError
