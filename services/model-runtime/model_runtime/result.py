"""Service return envelope: structured output + invocation telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from common_schemas import ModelInvocationTelemetry

T = TypeVar("T")


@dataclass(frozen=True)
class ReasoningCallResult(Generic[T]):
    output: T
    telemetry: ModelInvocationTelemetry
