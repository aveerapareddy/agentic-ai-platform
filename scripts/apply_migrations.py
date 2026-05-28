#!/usr/bin/env python3
"""Apply infra/db/migrations/*.sql in lexical order (local / CI / compose migrate job)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("ORCHESTRATOR_DATABASE_URL")
    if not url:
        msg = "Set DATABASE_URL or ORCHESTRATOR_DATABASE_URL"
        raise SystemExit(msg)
    return url


def apply_migrations(*, dry_run: bool = False) -> list[str]:
    mig_dir = _repo_root() / "infra" / "db" / "migrations"
    files = sorted(mig_dir.glob("*.sql"))
    if not files:
        raise SystemExit(f"No migrations found in {mig_dir}")
    applied: list[str] = []
    if dry_run:
        return [f.name for f in files]
    engine = create_engine(_database_url(), isolation_level="AUTOCOMMIT")
    for path in files:
        sql = path.read_text(encoding="utf-8")
        with engine.connect() as conn:
            conn.execute(text(sql))
        applied.append(path.name)
        print(f"applied {path.name}")
    return applied


def main() -> None:
    dry = "--dry-run" in sys.argv
    names = apply_migrations(dry_run=dry)
    if dry:
        print("would apply:", ", ".join(names))


if __name__ == "__main__":
    main()
