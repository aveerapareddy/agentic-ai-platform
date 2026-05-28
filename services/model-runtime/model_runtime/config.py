"""Runtime configuration from environment (no hardcoded secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ProviderType = Literal["fake", "openai", "azure_openai"]


@dataclass(frozen=True)
class ModelRuntimeConfig:
    provider_type: ProviderType = "fake"
    api_key: str | None = None
    base_url: str | None = None
    model_name: str = "gpt-4o-mini"
    azure_deployment: str | None = None
    azure_api_version: str = "2024-02-15-preview"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5


def load_config_from_env() -> ModelRuntimeConfig:
    provider_raw = os.environ.get("MODEL_PROVIDER", "fake").strip().lower()
    provider_type: ProviderType
    if provider_raw in ("openai", "openai_compatible"):
        provider_type = "openai"
    elif provider_raw in ("azure", "azure_openai", "azure_openai_compatible"):
        provider_type = "azure_openai"
    else:
        provider_type = "fake"

    api_key = (
        os.environ.get("MODEL_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("AZURE_OPENAI_API_KEY")
    )
    base_url = os.environ.get("MODEL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if provider_type == "openai" and not base_url:
        base_url = "https://api.openai.com/v1"
    if provider_type == "azure_openai":
        base_url = os.environ.get("AZURE_OPENAI_ENDPOINT") or base_url

    model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    timeout = float(os.environ.get("MODEL_TIMEOUT_SECONDS", "30"))
    max_retries = int(os.environ.get("MODEL_MAX_RETRIES", "2"))
    backoff = float(os.environ.get("MODEL_RETRY_BACKOFF_SECONDS", "0.5"))

    return ModelRuntimeConfig(
        provider_type=provider_type,
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        azure_api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        timeout_seconds=timeout,
        max_retries=max_retries,
        retry_backoff_seconds=backoff,
    )
