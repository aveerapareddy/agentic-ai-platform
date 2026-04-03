"""Minimal orchestrator configuration (Phase 1)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorSettings:
    """Deployment-tunable defaults; no env loading in Phase 1."""

    default_agent_reasoning: str = "reasoning_agent_v1"
    default_agent_validation: str = "validation_agent_v1"


@dataclass(frozen=True)
class DatabaseSettings:
    """PostgreSQL connection for PostgresRepository; unused for in-memory-only runs."""

    url: str
    echo_sql: bool = False

    @staticmethod
    def from_env() -> DatabaseSettings:
        """Read ORCHESTRATOR_DATABASE_URL, then DATABASE_URL, then local dev default."""
        default = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/orchestrator_dev"
        url = os.environ.get("ORCHESTRATOR_DATABASE_URL") or os.environ.get("DATABASE_URL", default)
        echo = os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes")
        return DatabaseSettings(url=url, echo_sql=echo)
