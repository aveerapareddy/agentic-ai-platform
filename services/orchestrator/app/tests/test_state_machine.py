"""Execution and step transition rules."""

from __future__ import annotations

import pytest
from common_schemas import ExecutionStatus, StepStatus

from app.runtime.state_machine import (
    InvalidStatusTransitionError,
    validate_execution_transition,
    validate_step_transition,
)


def test_execution_created_to_planning_ok() -> None:
    validate_execution_transition(ExecutionStatus.CREATED, ExecutionStatus.PLANNING)


def test_execution_planning_to_executing_ok() -> None:
    validate_execution_transition(ExecutionStatus.PLANNING, ExecutionStatus.EXECUTING)


def test_execution_completed_not_mutable() -> None:
    with pytest.raises(InvalidStatusTransitionError):
        validate_execution_transition(ExecutionStatus.COMPLETED, ExecutionStatus.EXECUTING)


def test_execution_invalid_skip_planning() -> None:
    with pytest.raises(InvalidStatusTransitionError):
        validate_execution_transition(ExecutionStatus.CREATED, ExecutionStatus.COMPLETED)


def test_execution_executing_to_completed_invalid() -> None:
    """Constitution §6.1: completion only after VALIDATING."""
    with pytest.raises(InvalidStatusTransitionError):
        validate_execution_transition(ExecutionStatus.EXECUTING, ExecutionStatus.COMPLETED)


def test_step_pending_to_running_to_succeeded() -> None:
    validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
    validate_step_transition(StepStatus.RUNNING, StepStatus.SUCCEEDED)


def test_step_running_to_pending_invalid() -> None:
    with pytest.raises(InvalidStatusTransitionError):
        validate_step_transition(StepStatus.RUNNING, StepStatus.PENDING)
