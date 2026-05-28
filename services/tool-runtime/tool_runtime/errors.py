"""Tool-runtime error taxonomy for retry classification."""

from __future__ import annotations


class ToolRuntimeError(Exception):
    """Base tool-runtime failure."""


class TransientToolError(ToolRuntimeError):
    """Retryable: timeout, simulated network, upstream unavailable."""


class ToolValidationError(ToolRuntimeError):
    """Non-retryable: malformed input or validation failure."""


class ToolCancelledError(ToolRuntimeError):
    """Non-retryable: cancellation requested before/during invoke."""
