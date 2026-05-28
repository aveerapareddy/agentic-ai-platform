"""SSE execution stream endpoint."""

from __future__ import annotations

import json
from uuid import UUID

from gateway.config import Settings
from gateway.main import create_app
from gateway.streaming.diff import diff_stream_events
from gateway.streaming.diff import StreamCursor
from gateway.tests.test_routes import _auth_headers, _base_context, _gateway
from fastapi.testclient import TestClient

from common_schemas import ExecutionStatus


def _parse_sse_events(body: str) -> list[dict]:
    events: list[dict] = []
    for block in body.split("\n\n"):
        if not block.strip() or block.strip().startswith(":"):
            continue
        data_line = next((ln for ln in block.split("\n") if ln.startswith("data: ")), None)
        if data_line:
            events.append(json.loads(data_line[6:]))
    return events


def test_stream_endpoint_content_type_and_events() -> None:
    with _gateway(schedule_start=True) as (c, _app):
        r = c.post(
            "/v1/executions",
            json={
                "workflow_type": "generic",
                "input": {"n": 1},
                "context": _base_context(),
            },
        )
        eid = r.json()["execution_id"]
        with c.stream(
            "GET",
            f"/v1/executions/{eid}/stream",
            headers=_auth_headers(),
            timeout=30,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            chunks = []
            for chunk in resp.iter_bytes():
                chunks.append(chunk)
                if len(b"".join(chunks)) > 200:
                    break
        body = b"".join(chunks).decode()
        parsed = _parse_sse_events(body)
        assert parsed
        types = {e["event_type"] for e in parsed}
        assert "execution_updated" in types or "trace_event" in types


def test_stream_requires_auth_when_fallback_disabled() -> None:
    app = create_app(Settings(allow_dev_principal_fallback=False, schedule_execution_start=False))
    with TestClient(app, raise_server_exceptions=True) as c:
        r = c.get(
            "/v1/executions/00000000-0000-4000-8000-000000000099/stream",
        )
        assert r.status_code == 401


def test_stream_tenant_forbidden() -> None:
    with _gateway() as (c, _app):
        r = c.post(
            "/v1/executions",
            headers=_auth_headers(tenant_id="tenant-stream-a"),
            json={"workflow_type": "generic", "input": {}, "context": _base_context()},
        )
        eid = r.json()["execution_id"]
        denied = c.get(
            f"/v1/executions/{eid}/stream",
            headers=_auth_headers(tenant_id="tenant-stream-b"),
        )
        assert denied.status_code == 403


def test_diff_emits_trace_and_terminal() -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from common_schemas import Execution, ExecutionMode

    now = datetime.now(timezone.utc)
    eid = uuid4()
    ex = Execution(
        execution_id=eid,
        workflow_type="generic",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=uuid4(),
        input={},
        result={"outcome": "success"},
        created_at=now,
        updated_at=now,
    )
    projection = {
        "timeline": [{"event_type": "execution_status", "at": now.isoformat(), "status": "completed"}],
        "steps": [],
        "approvals": [],
    }
    cursor = StreamCursor()
    events = diff_stream_events(execution=ex, trace_projection=projection, cursor=cursor)
    types = [e.event_type.value for e in events]
    assert "execution_updated" in types
    assert "execution_completed" in types
    assert "trace_event" in types
