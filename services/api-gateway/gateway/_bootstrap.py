"""Ensure monorepo service paths resolve when running the gateway without a pre-built venv layout."""

from __future__ import annotations

import sys
from pathlib import Path

_done = False


def ensure_platform_paths() -> None:
    """Insert common-schemas and orchestrator dependency roots before importing `app.*`."""
    global _done
    if _done:
        return
    services_root = Path(__file__).resolve().parents[2]
    repo_root = services_root.parent
    ordered = [
        repo_root / "packages" / "common-schemas" / "src",
        services_root / "policy-engine",
        services_root / "tool-runtime",
        services_root / "knowledge-service",
        services_root / "model-runtime",
        services_root / "feedback-service",
        services_root / "mukti-agent",
        services_root / "orchestrator",
    ]
    for p in ordered:
        s = str(p.resolve())
        if s not in sys.path:
            sys.path.insert(0, s)
    _done = True
