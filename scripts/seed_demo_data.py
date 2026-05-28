#!/usr/bin/env python3
"""Seed demo executions via api-gateway (deterministic; no fake platform behavior)."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install httpx: pip install httpx") from exc

_TERMINAL = frozenset({"completed", "failed", "cancelled", "awaiting_approval"})


def _gateway_url() -> str:
    return os.environ.get("GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "X-Principal-Id": os.environ.get("DEMO_PRINCIPAL_ID", "demo-seed"),
        "X-Tenant-Id": os.environ.get("DEMO_TENANT_ID", "dev-tenant"),
        "X-Roles": os.environ.get("DEMO_ROLES", "operator,admin,approver"),
        "Content-Type": "application/json",
    }


def _context(*, policy_scope: str = "default") -> dict[str, Any]:
    return {
        "request_id": "demo-seed",
        "environment": os.environ.get("DEMO_ENVIRONMENT", "dev"),
        "policy_scope": policy_scope,
    }


def wait_for_gateway(client: httpx.Client, timeout_sec: int = 60) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = client.get("/health/runtime", timeout=3.0)
            if r.status_code == 200 and r.json().get("status") == "ok":
                print("gateway healthy")
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise SystemExit(f"Gateway not healthy at {_gateway_url()} within {timeout_sec}s")


def wait_for_execution(client: httpx.Client, execution_id: str, timeout_sec: int = 180) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        r = client.get(f"/v1/executions/{execution_id}")
        r.raise_for_status()
        body = r.json()
        status = str(body.get("status", ""))
        if status in _TERMINAL:
            return body
        time.sleep(1)
    raise SystemExit(f"Execution {execution_id} did not reach terminal state in {timeout_sec}s")


def create_execution(
    client: httpx.Client,
    *,
    workflow_type: str,
    input_payload: dict[str, Any],
    idempotency_key: str,
    policy_scope: str = "default",
) -> str:
    r = client.post(
        "/v1/executions",
        json={
            "workflow_type": workflow_type,
            "input": input_payload,
            "context": _context(policy_scope=policy_scope),
            "idempotency_key": idempotency_key,
        },
    )
    if r.status_code == 201:
        eid = str(r.json()["execution_id"])
        print(f"created {workflow_type} execution {eid}")
        return eid
    if r.status_code == 400 and "idempotency" in r.text.lower():
        raise SystemExit("Idempotency conflict; use fresh DB or new DEMO_* keys")
    r.raise_for_status()
    raise SystemExit(f"unexpected status {r.status_code}: {r.text}")


def seed_incident(client: httpx.Client) -> str:
    eid = create_execution(
        client,
        workflow_type="incident_triage",
        input_payload={"incident_id": "demo-inc-001", "severity": "high"},
        idempotency_key="demo-seed-incident-v1",
    )
    final = wait_for_execution(client, eid)
    print(f"incident_triage terminal status={final.get('status')}")
    return eid


def seed_cost(client: httpx.Client) -> str:
    eid = create_execution(
        client,
        workflow_type="cost_attribution",
        input_payload={"scope_id": "demo-scope-001", "service_id": "payments-api"},
        idempotency_key="demo-seed-cost-v1",
    )
    final = wait_for_execution(client, eid)
    print(f"cost_attribution terminal status={final.get('status')}")
    return eid


def seed_replay(client: httpx.Client, source_id: str) -> str | None:
    r = client.post(
        f"/v1/executions/{source_id}/replay",
        json={
            "mode": "exact",
            "environment_target": "sandbox",
            "label": "demo-replay",
            "reason": "demo seed replay",
            "start_execution": True,
        },
    )
    if r.status_code != 202:
        print(f"replay skipped: {r.status_code} {r.text[:200]}")
        return None
    replay_id = str(r.json().get("replay_execution_id", ""))
    print(f"replay created {replay_id}")
    if replay_id:
        wait_for_execution(client, replay_id, timeout_sec=180)
    return replay_id


def seed_feedback(client: httpx.Client, execution_id: str) -> None:
    r = client.post(
        f"/v1/executions/{execution_id}/feedback",
        json={
            "source": "operator_console",
            "labels": ["demo", "seed"],
            "detail": {"note": "Seeded operator feedback for Mukti cross-execution insights."},
        },
    )
    if r.status_code == 201:
        print(f"operator feedback recorded for {execution_id}")
    else:
        print(f"feedback skipped: {r.status_code}")


def seed_mukti_insights(client: httpx.Client) -> None:
    r = client.get(
        "/v1/insights/mukti",
        params={"tenant_id": os.environ.get("DEMO_TENANT_ID", "dev-tenant"), "limit": 20},
    )
    if r.status_code == 200:
        data = r.json()
        print(
            f"mukti insights sample_size={data.get('execution_feedback_sample_size')} "
            f"insights={len(data.get('insights', []))}",
        )
    else:
        print(f"mukti insights skipped: {r.status_code}")


def main() -> None:
    base = _gateway_url()
    print(f"seeding via {base}")
    with httpx.Client(base_url=base, headers=_headers(), timeout=120.0) as client:
        wait_for_gateway(client)
        incident_id = seed_incident(client)
        cost_id = seed_cost(client)
        seed_replay(client, incident_id)
        seed_feedback(client, incident_id)
        seed_feedback(client, cost_id)
        seed_mukti_insights(client)
    print("demo seed complete")


if __name__ == "__main__":
    main()
