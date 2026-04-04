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

_INCIDENT_TRIAGE = "incident_triage"


class StepExecutor:
    """Bounded agent simulation: structured StepResult only; does not mutate execution state."""

    def execute_step(self, step: Step, *, now: datetime | None = None) -> StepResult:
        """Simulate work from workflow_type, step name, and type; traceable structured output (§4.1)."""
        if step.status != StepStatus.RUNNING:
            msg = f"step {step.step_id} must be RUNNING before execute_step(); got {step.status}"
            raise ValueError(msg)
        ts = now or datetime.now(timezone.utc)
        started = ts
        ended = ts

        workflow_type = step.input.get("workflow_type")
        step_name = step.input.get("planner_step_name")
        if workflow_type == _INCIDENT_TRIAGE and isinstance(step_name, str):
            return self._execute_incident_triage_step(step, step_name, ts, started, ended)

        return self._execute_generic_step(step, ts, started, ended)

    def _execute_incident_triage_step(
        self,
        step: Step,
        step_name: str,
        ts: datetime,
        started: datetime,
        ended: datetime,
    ) -> StepResult:
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        incident_key = str(ex_in.get("incident_id", ex_in.get("id", "unknown")))
        seed = hashlib.sha256(incident_key.encode()).hexdigest()[:8]
        digest = hashlib.sha256(
            json.dumps(
                {"step_name": step_name, "incident_key": incident_key, "simulated": True},
                sort_keys=True,
            ).encode(),
        ).hexdigest()[:16]

        causes_pool = ["config_drift", "dependency_failure", "capacity_saturation"]
        idx = int(seed[:2], 16) % len(causes_pool)
        likely = causes_pool[idx]

        if step_name == "analyze_incident":
            output: dict[str, object] = {
                "incident_summary": (
                    f"Incident {incident_key}: elevated error rate and latency correlated in window "
                    f"(deterministic triage digest {digest})"
                ),
                "possible_causes": list(causes_pool),
            }
            confidence = 0.84
            vo = None
        elif step_name == "gather_evidence":
            output = {
                "evidence_summary": (
                    f"Simulated correlation across metrics, logs, and deploy events for {incident_key} "
                    f"(seed {seed})"
                ),
                "signals": [
                    {"source": "metrics", "name": "error_rate", "detail": "spike vs baseline"},
                    {"source": "logs", "name": "timeout_pattern", "detail": f"ref:{digest}"},
                    {"source": "deploy", "name": "recent_change", "detail": "within lookback window"},
                ],
            }
            confidence = 0.81
            vo = None
        elif step_name == "validate_incident":
            val_status = "passed"
            conf = 0.92
            output = {
                "likely_cause": likely,
                "validation_status": val_status,
                "confidence_score": conf,
                "digest": digest,
            }
            confidence = conf
            vo = ValidationOutcome(
                status=val_status,
                details={
                    "likely_cause": likely,
                    "incident_key": incident_key,
                    "simulated": True,
                },
            )
        else:
            output = {"error": "unknown_planner_step_name", "step_name": step_name}
            confidence = 0.0
            vo = ValidationOutcome(status="failed", details={"reason": "unknown_step_name"})

        rid: ResultId = uuid4()
        evidence = [
            {
                "type": "simulated_incident_triage",
                "step_name": step_name,
                "ref": f"incident_triage:{digest}",
            }
        ]
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output=output,
            evidence=evidence,
            errors=[],
            latency_ms=1,
            latency_started_at=started,
            latency_ended_at=ended,
            confidence_score=confidence,
            confidence_detail={
                "source": "step_executor_incident_triage",
                "step_name": step_name,
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=vo,
            created_at=ts,
            updated_at=ts,
        )

    def _execute_generic_step(
        self,
        step: Step,
        ts: datetime,
        started: datetime,
        ended: datetime,
    ) -> StepResult:
        kind = step.step_type if isinstance(step.step_type, str) else step.step_type.value
        payload = {"step_id": str(step.step_id), "kind": kind, "simulated": True}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

        if kind == StepType.VALIDATION.value or kind == "validation":
            confidence = 0.95
            completeness = StepCompleteness.FULL
            output: dict[str, object] = {
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
