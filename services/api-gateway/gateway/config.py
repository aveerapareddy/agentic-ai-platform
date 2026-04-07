"""Gateway settings (auth hooks reserved; no full IAM in Phase 8)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=None, extra="ignore")

    app_name: str = "agentic-ai-platform-gateway"
    debug: bool = False
    schedule_execution_start: bool = True


def get_settings() -> Settings:
    return Settings()
