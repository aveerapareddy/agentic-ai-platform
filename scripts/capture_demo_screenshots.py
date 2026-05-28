#!/usr/bin/env python3
"""Capture demo screenshots from HTML fixtures (or live console when CAPTURE_LIVE=1)."""

from __future__ import annotations

import os
import sys
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

LIVE_ROUTES = [
    ("/executions", "01-execution-explorer.png"),
    ("/executions/a1b2c3d4-e5f6-7890-abcd-ef1234567890", "10-incident-triage-workflow.png"),
]


def capture_fixtures() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("pip install playwright && playwright install chromium") from exc

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for html_name, png_name in FIXTURE_MAP:
            path = FIXTURES / html_name
            if not path.exists():
                print(f"skip missing {path}")
                continue
            page.goto(path.as_uri())
            page.wait_for_timeout(200)
            out_path = OUT / png_name
            page.screenshot(path=str(out_path))
            print(f"wrote {out_path.relative_to(ROOT)}")
        browser.close()


def capture_live() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("pip install playwright && playwright install chromium") from exc

    base = os.environ.get("CONSOLE_URL", "http://127.0.0.1:4200").rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for route, png_name in LIVE_ROUTES:
            page.goto(f"{base}{route}")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / png_name))
            print(f"live {png_name}")
        browser.close()


def main() -> None:
    if os.environ.get("CAPTURE_LIVE", "").lower() in ("1", "true", "yes"):
        capture_live()
    else:
        capture_fixtures()
    print("capture complete")


if __name__ == "__main__":
    main()
