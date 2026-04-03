"""Local demo: create repository, run one execution, print summary."""

from __future__ import annotations

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService


def main() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)

    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "demo-1", "severity": "high"},
        tenant_id="tenant_demo",
        request_id="req-demo",
        environment="dev",
        policy_scope="default",
    )
    print("created:", ex.execution_id, ex.status)

    done = svc.start_execution(ex.execution_id)
    print("final:", done.execution_id, done.status)
    print("result:", done.result)
    for step in repo.list_steps_for_execution(done.execution_id):
        print(" step", step.step_id, step.step_type, step.status)
        r = repo.get_step_result(step.step_id)
        if r:
            print("  confidence_score", r.confidence_score, "completeness", r.completeness)


if __name__ == "__main__":
    main()
