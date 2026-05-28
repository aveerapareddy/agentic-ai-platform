"""RBAC coverage for metrics, insights, operational endpoints, replay, stream, cancel."""

from __future__ import annotations

from gateway.config import Settings
from gateway.main import create_app
from gateway.tests.test_routes import _auth_headers, _base_context, _gateway
from fastapi.testclient import TestClient


def test_unauthenticated_business_metrics_when_fallback_disabled() -> None:
    app = create_app(Settings(allow_dev_principal_fallback=False, schedule_execution_start=False))
    with TestClient(app, raise_server_exceptions=True) as c:
        assert c.get("/v1/metrics").status_code == 401
        assert c.get("/v1/insights/mukti").status_code == 401


def test_viewer_can_read_aggregated_metrics() -> None:
    with _gateway() as (c, _app):
        r = c.get("/v1/metrics", headers=_auth_headers(roles="viewer"))
        assert r.status_code == 200, r.text


def test_viewer_cannot_read_metrics_with_foreign_tenant_query() -> None:
    with _gateway() as (c, _app):
        r = c.get(
            "/v1/metrics",
            headers=_auth_headers(roles="viewer", tenant_id="tenant-a"),
            params={"tenant_id": "tenant-b"},
        )
        assert r.status_code == 403


def test_viewer_can_read_mukti_insights() -> None:
    with _gateway() as (c, _app):
        r = c.get("/v1/insights/mukti", headers=_auth_headers(roles="viewer"))
        assert r.status_code == 200, r.text


def test_viewer_cannot_create_replay() -> None:
    with _gateway() as (c, _app):
        create = c.post(
            "/v1/executions",
            json={"workflow_type": "generic", "input": {}, "context": _base_context()},
        )
        eid = create.json()["execution_id"]
        denied = c.post(
            f"/v1/executions/{eid}/replay",
            headers=_auth_headers(roles="viewer"),
            json={"mode": "exact", "start_execution": False},
        )
        assert denied.status_code == 403


def test_viewer_cannot_cancel_execution() -> None:
    with _gateway() as (c, _app):
        create = c.post(
            "/v1/executions",
            json={"workflow_type": "generic", "input": {}, "context": _base_context()},
        )
        eid = create.json()["execution_id"]
        denied = c.post(
            f"/v1/executions/{eid}/cancel",
            headers=_auth_headers(roles="viewer"),
        )
        assert denied.status_code == 403


def test_operational_endpoints_public_without_auth() -> None:
    app = create_app(Settings(allow_dev_principal_fallback=False, schedule_execution_start=False))
    with TestClient(app, raise_server_exceptions=True) as c:
        health = c.get("/health/runtime")
        assert health.status_code == 200
        assert health.json().get("status") == "ok"
        metrics = c.get("/metrics")
        assert metrics.status_code == 200
        assert "text/plain" in metrics.headers.get("content-type", "")


def test_policy_simulate_still_admin_only() -> None:
    with _gateway() as (c, _app):
        denied = c.post(
            "/v1/policies/simulate",
            headers=_auth_headers(roles="operator"),
            json={
                "action_type": "escalate_incident",
                "risk_level": "high",
                "execution_context": {"environment": "dev", "policy_scope": "default"},
            },
        )
        assert denied.status_code == 403


def test_policy_simulate_increments_counters() -> None:
    from observability.metrics import get_registry

    reg = get_registry()
    reg.reset()
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/policies/simulate",
            headers=_auth_headers(roles="admin"),
            json={
                "action_type": "escalate_incident",
                "risk_level": "high",
                "execution_context": {"environment": "dev", "policy_scope": "default"},
            },
        )
        assert r.status_code == 200
    snap = reg.snapshot()["counters"]
    assert snap.get(("policy_simulations_total", ()), 0) >= 1
    assert snap.get(("policy_evaluations_total", ()), 0) >= 1
    assert snap.get(("policy_decision_allow_total", ()), 0) >= 1
