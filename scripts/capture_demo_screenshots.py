#!/usr/bin/env python3
"""Capture demo screenshots from HTML fixtures (or live console when CAPTURE_LIVE=1)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs" / "assets" / "screenshot-fixtures"
OUT = ROOT / "docs" / "assets" / "screenshots"

FIXTURE_MAP = [
    ("01-execution-explorer.html", "01-execution-explorer.png"),
    ("02-execution-detail.html", "02-execution-detail.png"),
    ("03-trace-timeline.html", "03-trace-timeline.png"),
    ("04-replay-comparison.html", "04-replay-comparison.png"),
    ("05-metrics-evaluation.html", "05-metrics-evaluation.png"),
    ("06-mukti-insights.html", "06-mukti-insights.png"),
    ("07-policy-simulation.html", "07-policy-simulation.png"),
    ("08-streaming-execution.html", "08-streaming-execution.png"),
    ("09-cost-attribution-workflow.html", "09-cost-attribution-workflow.png"),
    ("10-incident-triage-workflow.html", "10-incident-triage-workflow.png"),
]

DEFAULT_HEADERS = {
    "X-Principal-Id": "console-operator",
    "X-Tenant-Id": "dev-tenant",
    "X-Roles": "operator,admin",
}


@dataclass(frozen=True)
class LiveCapture:
    route: str
    png: str
    wait_selector: str = ".oc-page-content, .oc-main, app-page-header"
    scroll_to: str | None = None


def _discover_demo_ids(gateway: str) -> tuple[str, str, str, str]:
    """Return incident_id, cost_id, source_id, replay_id from gateway list + detail."""
    url = f"{gateway.rstrip('/')}/v1/executions?limit=50"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    items = data.get("items") or []
    incident = next((i["execution_id"] for i in items if i.get("workflow_type") == "incident_triage"), None)
    cost = next((i["execution_id"] for i in items if i.get("workflow_type") == "cost_attribution"), None)
    if not incident or not cost:
        raise SystemExit("Need seeded incident_triage and cost_attribution executions on api-gateway")

    source = incident
    replay = incident
    for item in items:
        eid = item["execution_id"]
        detail_url = f"{gateway.rstrip('/')}/v1/executions/{eid}"
        try:
            dreq = urllib.request.Request(detail_url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(dreq, timeout=15) as dresp:
                detail = json.loads(dresp.read().decode())
            parent = detail.get("parent_execution_id")
            if parent:
                source = parent
                replay = eid
                break
        except urllib.error.HTTPError:
            continue
    return incident, cost, source, replay


def live_captures(gateway: str) -> list[LiveCapture]:
    incident, cost, source, replay = _discover_demo_ids(gateway)
    print(f"demo ids: incident={incident[:8]}… cost={cost[:8]}… replay={replay[:8]}… source={source[:8]}…")
    return [
        LiveCapture("/executions", "01-execution-explorer.png", ".oc-table, .oc-empty-state, .oc-filters"),
        LiveCapture(f"/executions/{incident}", "02-execution-detail.png", ".oc-exec-ribbon"),
        LiveCapture(
            f"/executions/{incident}",
            "03-trace-timeline.png",
            ".tl-step-group, .oc-timeline-panel, .trace-timeline",
            scroll_to="#timeline",
        ),
        LiveCapture(
            f"/executions/{source}/replay-diff/{replay}",
            "04-replay-comparison.png",
            ".oc-replay-banner, .oc-panel",
        ),
        LiveCapture("/metrics", "05-metrics-evaluation.png", ".oc-stat-row, .oc-table, .oc-filters"),
        LiveCapture(
            "/insights",
            "06-mukti-insights.png",
            ".oc-insight-grid, .oc-rank-item, .oc-stat-row, .oc-empty-state",
        ),
        LiveCapture("/policies", "07-policy-simulation.png", ".oc-filters, .oc-panel, form"),
        LiveCapture("/live", "08-streaming-execution.png", ".oc-live-rail, .oc-live-card, .oc-empty-state"),
        LiveCapture(f"/executions/{cost}", "09-cost-attribution-workflow.png", ".oc-exec-ribbon"),
        LiveCapture(
            f"/executions/{incident}",
            "10-incident-triage-workflow.png",
            ".oc-exec-ribbon",
            scroll_to="#lifecycle",
        ),
    ]


def capture_fixtures() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("pip install playwright && playwright install chromium") from exc

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for html_name, png_name in FIXTURE_MAP:
            path = FIXTURES / html_name
            if not path.exists():
                print(f"skip missing {path}")
                continue
            page.goto(path.as_uri())
            page.wait_for_timeout(300)
            out_path = OUT / png_name
            page.screenshot(path=str(out_path), full_page=True)
            print(f"wrote {out_path.relative_to(ROOT)}")
        browser.close()


def _wait_any(page, selectors: str, timeout_ms: int = 20_000) -> None:
    for sel in selectors.split(","):
        sel = sel.strip()
        if not sel:
            continue
        try:
            page.wait_for_selector(sel, timeout=timeout_ms, state="visible")
            return
        except Exception:
            continue
    page.wait_for_timeout(1500)


def capture_live() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("pip install playwright && playwright install chromium") from exc

    console = os.environ.get("CONSOLE_URL", "http://127.0.0.1:4200").rstrip("/")
    gateway = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)

    try:
        captures = live_captures(gateway)
    except Exception as exc:
        print(f"live id discovery failed ({exc}); falling back to fixtures")
        capture_fixtures()
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for shot in captures:
            page.goto(f"{console}{shot.route}", wait_until="networkidle", timeout=60_000)
            _wait_any(page, shot.wait_selector)
            page.wait_for_timeout(400)
            if shot.scroll_to:
                loc = page.locator(shot.scroll_to)
                if loc.count():
                    loc.first.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
            out_path = OUT / shot.png
            page.screenshot(path=str(out_path), full_page=False)
            print(f"live {shot.png} <- {shot.route}")
        browser.close()


def main() -> None:
    if os.environ.get("CAPTURE_LIVE", "").lower() in ("1", "true", "yes"):
        capture_live()
    else:
        capture_fixtures()
    print("capture complete")


if __name__ == "__main__":
    main()
