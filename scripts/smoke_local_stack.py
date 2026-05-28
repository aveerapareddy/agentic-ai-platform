#!/usr/bin/env python3
"""Lightweight local stack smoke checks (gateway; optional console). Exit 0 on success."""

from __future__ import annotations

import os
import sys

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install httpx: pip install httpx") from exc


def _gateway_url() -> str:
    return os.environ.get("GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")


def _console_url() -> str:
    return os.environ.get("CONSOLE_URL", "http://127.0.0.1:4200").rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "X-Principal-Id": os.environ.get("DEMO_PRINCIPAL_ID", "demo-smoke"),
        "X-Tenant-Id": os.environ.get("DEMO_TENANT_ID", "dev-tenant"),
        "X-Roles": os.environ.get("DEMO_ROLES", "viewer,operator,admin"),
    }


def check_gateway(client: httpx.Client) -> None:
    health = client.get("/health/runtime", timeout=5.0)
    health.raise_for_status()
    body = health.json()
    if body.get("status") != "ok":
        raise SystemExit(f"unexpected health body: {body}")
    print("ok: GET /health/runtime")

    prom = client.get("/metrics", timeout=5.0)
    prom.raise_for_status()
    if "policy_evaluations_total" not in prom.text and "#" in prom.text:
        pass  # counters appear after first evaluation; absence is not a hard fail
    print("ok: GET /metrics (operational)")

    authed = httpx.Client(base_url=_gateway_url(), headers=_headers(), timeout=10.0)
    try:
        metrics = authed.get("/v1/metrics", params={"limit": 5})
        if metrics.status_code == 401:
            raise SystemExit("GET /v1/metrics returned 401; set GATEWAY_ALLOW_DEV_PRINCIPAL_FALLBACK or auth headers")
        metrics.raise_for_status()
        print("ok: GET /v1/metrics (authenticated)")

        listings = authed.get("/v1/executions", params={"limit": 5})
        listings.raise_for_status()
        count = len(listings.json().get("items", []))
        print(f"ok: GET /v1/executions ({count} items)")
    finally:
        authed.close()


def check_console() -> None:
    if os.environ.get("SMOKE_SKIP_CONSOLE", "").lower() in ("1", "true", "yes"):
        print("skip: console check (SMOKE_SKIP_CONSOLE)")
        return
    url = _console_url()
    try:
        r = httpx.get(url, timeout=5.0, follow_redirects=True)
        r.raise_for_status()
        print(f"ok: console reachable at {url}")
    except httpx.HTTPError as exc:
        print(f"warn: console not reachable at {url}: {exc}", file=sys.stderr)


def main() -> None:
    base = _gateway_url()
    print(f"smoke: gateway {base}")
    with httpx.Client(base_url=base, timeout=10.0) as client:
        check_gateway(client)
    check_console()
    print("smoke complete")


if __name__ == "__main__":
    main()
