"""Simulated step work: deterministic, no external I/O (tools/knowledge are separate services)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    ResultId,
    Step,
    StepCompleteness,
    StepResult,
    StepStatus,
    StepType,
    ValidationOutcome,
)


class StepExecutor:
    """Bounded agent simulation: structured StepResult only; does not mutate execution state."""

    def execute_step(self, step: Step, *, now: datetime | None = None) -> StepResult:
        """Simulate work from step id and type; records evidence for traceability (constitution §4.1)."""
        if step.status != StepStatus.RUNNING:
            msg = f"step {step.step_id} must be RUNNING before execute_step(); got {step.status}"
            raise ValueError(msg)
        ts = now or datetime.now(timezone.utc)
        started = ts
        ended = ts

        kind = step.step_type if isinstance(step.step_type, str) else step.step_type.value
        payload = {"step_id": str(step.step_id), "kind": kind, "simulated": True}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

        if kind == StepType.VALIDATION.value or kind == "validation":
            confidence = 0.95
            completeness = StepCompleteness.FULL
            output = {
                "validated": True,
                "digest": digest,
                "summary": "validation passed (simulated)",
            }
            validation_outcome = ValidationOutcome(
                status="passed",
                details={"simulated": True, "digest": digest},
            )
        else:
            confidence = 0.82
            completeness = StepCompleteness.FULL
            output = {
                "reasoning_digest": digest,
                "summary": "reasoning completed (simulated)",
            }
            validation_outcome = None

        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output=output,
            evidence=[{"type": "simulated", "ref": f"sim:{digest}"}],
            errors=[],
            latency_ms=1,
            latency_started_at=started,
            latency_ended_at=ended,
            confidence_score=confidence,
            confidence_detail={"source": "step_executor_simulator", "kind": kind},
            completeness=completeness,
            validation_outcome=validation_outcome,
            created_at=ts,
            updated_at=ts,
        )
