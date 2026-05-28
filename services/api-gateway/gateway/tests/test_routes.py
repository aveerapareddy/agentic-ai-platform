"""Route-level tests: gateway delegates to in-process orchestrator and feedback-service."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.main import create_app


@contextmanager
def _gateway(
    *,
    schedule_start: bool = False,
    use_worker_queue: bool = False,
) -> Iterator[tuple[TestClient, FastAPI]]:
    app = create_app(
        Settings(
            schedule_execution_start=schedule_start,
            use_execution_worker_queue=use_worker_queue,
        ),
    )
    with TestClient(app, raise_server_exceptions=True, headers=_auth_headers()) as c:
        yield c, app


def _auth_headers(
    *,
    tenant_id: str = "t-gateway",
    principal_id: str = "test-operator",
    roles: str = "operator,admin",
) -> dict[str, str]:
    return {
        "X-Principal-Id": principal_id,
        "X-Tenant-Id": tenant_id,
        "X-Roles": roles,
    }


def _base_context(**overrides: str) -> dict:
    base = {
        "request_id": "req-1",
        "environment": "dev",
        "policy_scope": "default",
    }
    base.update(overrides)
    return base


def test_create_and_get_execution() -> None:
    with _gateway() as (c, _app):
        body = {
            "workflow_type": "incident_triage",
            "input": {"incident_id": "g1", "severity": "low"},
            "context": _base_context(),
        }
        r = c.post("/v1/executions", json=body)
        assert r.status_code == 201, r.text
        data = r.json()
        eid = data["execution_id"]
        assert data["status"] == "created"
        g = c.get(f"/v1/executions/{eid}")
        assert g.status_code == 200
        assert g.json()["workflow_type"] == "incident_triage"


def test_list_executions() -> None:
    with _gateway() as (c, _app):
        for i in range(2):
            c.post(
                "/v1/executions",
                json={
                    "workflow_type": "generic",
                    "input": {"n": i},
                    "context": _base_context(request_id=f"r{i}"),
                },
            )
        r = c.get("/v1/executions", params={"tenant_id": "t-gateway", "limit": 10})
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 2


def test_trace_retrieval() -> None:
    with _gateway(schedule_start=True) as (c, _app):
        body = {
            "workflow_type": "incident_triage",
            "input": {"incident_id": "tr1", "severity": "low"},
            "context": _base_context(),
        }
        r = c.post("/v1/executions", json=body)
        eid = r.json()["execution_id"]
        tr = c.get(f"/v1/executions/{eid}/trace")
        assert tr.status_code == 200
        tj = tr.json()
        assert tj["execution_id"] == eid
        assert "timeline" in tj
        assert "steps" in tj


def test_approval_submission() -> None:
    _app = create_app(Settings(schedule_execution_start=False))
    with TestClient(_app, raise_server_exceptions=True, headers=_auth_headers(roles="approver,admin")) as c:
        app = _app
        body = {
            "workflow_type": "incident_triage",
            "input": {"id": "ap1"},
            "context": _base_context(policy_scope="phase3_conditional"),
        }
        r = c.post("/v1/executions", json=body)
        eid = UUID(r.json()["execution_id"])
        paused = app.state.gateway.execution_service.start_execution(eid)
        assert paused.status.value == "awaiting_approval"
        gov = paused.result.get("governance") if paused.result else {}
        apr = c.post(
            f"/v1/executions/{eid}/approvals",
            json={
                "action_proposal_id": gov.get("proposal_id"),
                "policy_evaluation_id": gov.get("evaluation_id"),
                "decision": "approve",
                "approver": "gateway-test",
            },
        )
        assert apr.status_code == 201, apr.text
        assert apr.json()["decision"] == "approve"


def test_feedback_submission() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            json={
                "workflow_type": "incident_triage",
                "input": {"incident_id": "fb1"},
                "context": _base_context(),
            },
        )
        eid = r.json()["execution_id"]
        fr = c.post(
            f"/v1/executions/{eid}/feedback",
            json={"source": "operator_console", "labels": ["test"], "detail": {"comment": "ok"}},
        )
        assert fr.status_code == 201, fr.text
        assert fr.json()["execution_id"] == eid


def test_replay_shape() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            json={
                "workflow_type": "generic",
                "input": {"x": 1},
                "context": _base_context(),
            },
        )
        src = r.json()["execution_id"]
        rep = c.post(
            f"/v1/executions/{src}/replay",
            json={"mode": "exact", "environment_target": "sandbox", "label": "unit"},
        )
        assert rep.status_code == 202, rep.text
        body = rep.json()
        assert body["source_execution_id"] == src
        assert body["replay_mode"] == "exact"
        assert body["status"] == "created"
        assert "replay_execution_id" in body
        assert "provenance" in body
        assert body["provenance"]["source_execution_id"] == src
        assert body["provenance"]["label"] == "unit"

        child = c.get(f"/v1/executions/{body['replay_execution_id']}")
        assert child.status_code == 200
        child_body = child.json()
        assert child_body.get("parent_execution_id") == src

        diff = c.get(f"/v1/executions/{src}/replay-diff/{body['replay_execution_id']}")
        assert diff.status_code == 200, diff.text
        diff_body = diff.json()
        assert diff_body["source_execution_id"] == src
        assert diff_body["replay_execution_id"] == body["replay_execution_id"]
        assert diff_body["linked_to_source"] is True
        assert "total_differences" in diff_body
        assert "items" in diff_body
        assert isinstance(diff_body["items"], list)


def test_get_execution_not_found() -> None:
    with _gateway() as (c, _app):
        r = c.get("/v1/executions/00000000-0000-4000-8000-000000000001")
        assert r.status_code == 404


@pytest.mark.parametrize("workflow", ["incident_triage", "generic"])
def test_supported_workflow_types(workflow: str) -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            json={"workflow_type": workflow, "input": {}, "context": _base_context()},
        )
        assert r.status_code == 201, r.text


def test_get_execution_metrics() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            json={
                "workflow_type": "generic",
                "input": {"n": 1},
                "context": _base_context(),
            },
        )
        eid = r.json()["execution_id"]
        mr = c.get(f"/v1/executions/{eid}/metrics")
        assert mr.status_code == 200, mr.text
        body = mr.json()
        assert body["execution_id"] == eid
        assert body["workflow_type"] == "generic"
        assert "model_fallback_rate" in body
        assert "tool_success_rate" in body
        assert "computation_notes" in body


def test_get_execution_metrics_not_found() -> None:
    with _gateway() as (c, _app):
        r = c.get("/v1/executions/00000000-0000-4000-8000-000000000099/metrics")
        assert r.status_code == 404


def test_get_aggregated_metrics() -> None:
    with _gateway() as (c, _app):
        c.post(
            "/v1/executions",
            json={
                "workflow_type": "generic",
                "input": {},
                "context": _base_context(),
            },
        )
        r = c.get("/v1/metrics", params={"tenant_id": "t-gateway", "limit": 20})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "executions_in_scope" in data
        assert "by_workflow_type" in data
        assert "by_step_type" in data
        assert "by_tool_name" in data
        assert "by_policy_decision" in data
        assert data["executions_in_scope"] >= 1


def test_get_anomalies_insight_shape() -> None:
    with _gateway() as (c, _app):
        r = c.get("/v1/insights/anomalies", params={"tenant_id": "t-gateway", "limit": 10})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "scope_description" in data
        assert "execution_sample_size" in data
        assert "anomalies" in data
        assert isinstance(data["anomalies"], list)
        for item in data["anomalies"]:
            assert set(item.keys()) >= {"code", "severity", "explanation", "evidence"}


def test_get_mukti_insights_shape() -> None:
    with _gateway() as (c, app):
        r = c.get("/v1/insights/mukti", params={"tenant_id": "t-gateway", "limit": 20})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "scope_description" in data
        assert "execution_feedback_sample_size" in data
        assert "top_failure_types" in data
        assert "recurring_patterns" in data
        assert "policy_friction_areas" in data
        assert "model_fallback_concentration" in data
        assert "unstable_workflows_or_steps" in data
        assert "ranked_improvement_suggestions" in data
        assert "insights" in data
        assert isinstance(data["insights"], list)


def test_get_mukti_insight_by_id_not_found() -> None:
    with _gateway() as (c, _app):
        r = c.get(
            "/v1/insights/mukti/00000000-0000-4000-8000-000000000099",
            params={"tenant_id": "t-gateway"},
        )
        assert r.status_code == 404


def test_operational_metrics_and_runtime_health() -> None:
    with _gateway() as (c, _app):
        m = c.get("/metrics")
        assert m.status_code == 200
        assert "text/plain" in m.headers.get("content-type", "")
        h = c.get("/health/runtime")
        assert h.status_code == 200
        body = h.json()
        assert body["status"] == "ok"
        assert "model_provider" in body
