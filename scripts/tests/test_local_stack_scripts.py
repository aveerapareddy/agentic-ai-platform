"""Smoke tests for migration and seed script modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_apply_migrations_dry_run_lists_sql_files() -> None:
    root = Path(__file__).resolve().parents[2]
    mod = _load_module("apply_migrations", root / "scripts" / "apply_migrations.py")
    names = mod.apply_migrations(dry_run=True)
    assert "001_initial_schema.sql" in names
    assert "002_operator_feedback.sql" in names


def test_seed_module_has_main() -> None:
    root = Path(__file__).resolve().parents[2]
    mod = _load_module("seed_demo_data", root / "scripts" / "seed_demo_data.py")
    assert callable(mod.main)
    assert mod._TERMINAL
