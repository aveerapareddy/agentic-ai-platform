"""Execution and step transitions; must match runtime model and project constitution."""

from __future__ import annotations

from common_schemas import ExecutionStatus, StepStatus


class InvalidStatusTransitionError(ValueError):
    """Raised when a lifecycle transition is not permitted."""


# EXECUTING -> COMPLETED is intentionally omitted: constitution §6.1 requires explicit validation phase.
_EXECUTION_ALLOWED: set[tuple[ExecutionStatus, ExecutionStatus]] = {
    (ExecutionStatus.CREATED, ExecutionStatus.PLANNING),
    (ExecutionStatus.CREATED, ExecutionStatus.FAILED),
    (ExecutionStatus.PLANNING, ExecutionStatus.EXECUTING),
    (ExecutionStatus.PLANNING, ExecutionStatus.FAILED),
    (ExecutionStatus.EXECUTING, ExecutionStatus.VALIDATING),
    (ExecutionStatus.EXECUTING, ExecutionStatus.FAILED),
    (ExecutionStatus.EXECUTING, ExecutionStatus.CANCELLED),
    (ExecutionStatus.VALIDATING, ExecutionStatus.COMPLETED),
    (ExecutionStatus.VALIDATING, ExecutionStatus.EXECUTING),
    (ExecutionStatus.VALIDATING, ExecutionStatus.FAILED),
}

_STEP_ALLOWED: set[tuple[StepStatus, StepStatus]] = {
    (StepStatus.PENDING, StepStatus.RUNNING),
    (StepStatus.PENDING, StepStatus.SKIPPED),
    (StepStatus.PENDING, StepStatus.CANCELLED),
    (StepStatus.RUNNING, StepStatus.SUCCEEDED),
    (StepStatus.RUNNING, StepStatus.FAILED),
    (StepStatus.RUNNING, StepStatus.CANCELLED),
}

_EXECUTION_TERMINAL = frozenset(
    {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    }
)

_STEP_TERMINAL = frozenset(
    {
        StepStatus.SUCCEEDED,
        StepStatus.FAILED,
        StepStatus.SKIPPED,
        StepStatus.CANCELLED,
    }
)


def validate_execution_transition(from_status: ExecutionStatus, to_status: ExecutionStatus) -> None:
    """Raise InvalidStatusTransitionError if execution cannot move from `from_status` to `to_status`."""
    if from_status in _EXECUTION_TERMINAL and from_status != to_status:
        msg = f"execution is terminal ({from_status.value}); cannot transition to {to_status.value}"
        raise InvalidStatusTransitionError(msg)
    if (from_status, to_status) not in _EXECUTION_ALLOWED:
        msg = f"invalid execution transition: {from_status.value} -> {to_status.value}"
        raise InvalidStatusTransitionError(msg)


def validate_step_transition(from_status: StepStatus, to_status: StepStatus) -> None:
    """Raise InvalidStatusTransitionError if step cannot move from `from_status` to `to_status`."""
    if from_status in _STEP_TERMINAL and from_status != to_status:
        msg = f"step is terminal ({from_status.value}); cannot transition to {to_status.value}"
        raise InvalidStatusTransitionError(msg)
    if (from_status, to_status) not in _STEP_ALLOWED:
        msg = f"invalid step transition: {from_status.value} -> {to_status.value}"
        raise InvalidStatusTransitionError(msg)


def is_execution_terminal(status: ExecutionStatus) -> bool:
    return status in _EXECUTION_TERMINAL


def is_step_terminal(status: StepStatus) -> bool:
    return status in _STEP_TERMINAL
