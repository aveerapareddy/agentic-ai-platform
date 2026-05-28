"""Gateway settings (auth hooks reserved; no full IAM in Phase 8)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=None, extra="ignore")

    app_name: str = "agentic-ai-platform-gateway"
    debug: bool = False
    schedule_execution_start: bool = True
    use_execution_worker_queue: bool = True
    allow_dev_principal_fallback: bool = True
    dev_principal_id: str = "dev-operator"
    dev_tenant_id: str = "dev-tenant"
    dev_roles: str = "operator,admin"


def get_settings() -> Settings:
    return Settings()
