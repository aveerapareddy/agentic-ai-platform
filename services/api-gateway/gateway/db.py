"""Repository factory for api-gateway (in-memory vs PostgreSQL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gateway.config import Settings

if TYPE_CHECKING:
    from app.adapters.repository import InMemoryRepository, PostgresRepository

RepositoryT = "InMemoryRepository | PostgresRepository"


def build_repository(settings: Settings) -> RepositoryT:
    if not settings.use_postgres:
        from app.adapters.repository import InMemoryRepository

        return InMemoryRepository()

    from app.adapters.db import create_engine_from_settings, create_session_factory
    from app.adapters.repository import PostgresRepository
    from app.config import DatabaseSettings

    db = DatabaseSettings.from_env()
    engine = create_engine_from_settings(db)
    factory = create_session_factory(engine)
    return PostgresRepository(factory)


def build_feedback_repository(settings: Settings):
    if not settings.use_postgres:
        from feedback_service.repository import InMemoryFeedbackRepository

        return InMemoryFeedbackRepository()

    from app.adapters.db import create_engine_from_settings, create_session_factory
    from app.config import DatabaseSettings
    from feedback_service.repository import PostgresFeedbackRepository

    db = DatabaseSettings.from_env()
    engine = create_engine_from_settings(db)
    factory = create_session_factory(engine)
    return PostgresFeedbackRepository(factory)
