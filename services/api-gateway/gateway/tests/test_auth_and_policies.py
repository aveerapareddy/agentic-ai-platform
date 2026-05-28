"""Session E: auth headers, RBAC, tenant propagation, policy APIs."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.main import create_app
from gateway.tests.test_routes import _auth_headers, _base_context, _gateway


def test_missing_auth_returns_401_when_dev_fallback_disabled() -> None:
    app = create_app(Settings(allow_dev_principal_fallback=False, schedule_execution_start=False))
    with TestClient(app, raise_server_exceptions=True) as c:
        r = c.get("/v1/executions")
        assert r.status_code == 401


def test_viewer_cannot_create_execution() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            headers=_auth_headers(roles="viewer"),
            json={
                "workflow_type": "generic",
                "input": {},
                "context": _base_context(),
            },
        )
        assert r.status_code == 403


def test_tenant_propagation_ignores_conflicting_body_tenant() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            json={
                "workflow_type": "generic",
                "input": {},
                "context": {**_base_context(), "tenant_id": "other-tenant"},
            },
        )
        assert r.status_code == 400


def test_execution_create_uses_auth_tenant() -> None:
    with _gateway() as (c, app):
        r = c.post(
            "/v1/executions",
            headers=_auth_headers(tenant_id="tenant-a"),
            json={
                "workflow_type": "generic",
                "input": {},
                "context": _base_context(),
            },
        )
        assert r.status_code == 201, r.text
        eid = UUID(r.json()["execution_id"])
        ex = app.state.gateway.repository.get_execution(eid)
        assert ex is not None
        ctx = app.state.gateway.repository.get_context(ex.execution_context_id)
        assert ctx is not None
        assert ctx.tenant_id == "tenant-a"
        assert ctx.principal_id == "test-operator"


def test_cross_tenant_execution_read_forbidden() -> None:
    with _gateway() as (c, app):
        r = c.post(
            "/v1/executions",
            headers=_auth_headers(tenant_id="tenant-a"),
            json={"workflow_type": "generic", "input": {}, "context": _base_context()},
        )
        eid = r.json()["execution_id"]
        forbidden = c.get(
            f"/v1/executions/{eid}",
            headers=_auth_headers(tenant_id="tenant-b"),
        )
        assert forbidden.status_code == 403


def test_list_policies_requires_admin() -> None:
    with _gateway() as (c, _app):
        denied = c.get("/v1/policies", headers=_auth_headers(roles="operator"))
        assert denied.status_code == 403
        ok = c.get("/v1/policies", headers=_auth_headers(roles="admin"))
        assert ok.status_code == 200
        body = ok.json()
        assert body["rule_pack_id"]
        assert len(body["rules"]) >= 1
        assert body["rules"][0]["rule_id"]


def test_policy_simulate_allow_deny_conditional() -> None:
    with _gateway() as (c, _app):
        allow = c.post(
            "/v1/policies/simulate",
            headers=_auth_headers(roles="admin"),
            json={
                "action_type": "escalate_incident",
                "risk_level": "high",
                "execution_context": {"environment": "dev", "policy_scope": "default"},
            },
        )
        assert allow.status_code == 200, allow.text
        assert allow.json()["decision"] == "allow"

        deny = c.post(
            "/v1/policies/simulate",
            headers=_auth_headers(roles="admin"),
            json={
                "action_type": "escalate_incident",
                "risk_level": "high",
                "execution_context": {"environment": "dev", "policy_scope": "phase3_deny"},
            },
        )
        assert deny.json()["decision"] == "deny"

        cond = c.post(
            "/v1/policies/simulate",
            headers=_auth_headers(roles="admin"),
            json={
                "action_type": "escalate_incident",
                "risk_level": "high",
                "execution_context": {"environment": "prod", "policy_scope": "default"},
            },
        )
        assert cond.json()["decision"] == "conditional"
        assert cond.json()["rule_references"]
