"""SQLAlchemy engine and session factory (PostgreSQL only; orchestrator runtime stays agnostic)."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DatabaseSettings


def create_engine_from_settings(settings: DatabaseSettings) -> Engine:
    """Create a sync engine with pre-ping for resilient pools."""
    return create_engine(
        settings.url,
        pool_pre_ping=True,
        echo=settings.echo_sql,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory: one session per repository operation (caller commits)."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
