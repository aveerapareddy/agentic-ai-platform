"""Build injectable provider from configuration."""

from __future__ import annotations

from typing import Any

from model_runtime.config import ModelRuntimeConfig
from model_runtime.errors import NonRetryableModelError
from model_runtime.providers.fake import FakeStructuredProvider
from model_runtime.providers.openai_compatible import AzureOpenAICompatibleProvider, OpenAICompatibleProvider


def build_provider(config: ModelRuntimeConfig | None = None) -> Any:
    cfg = config or ModelRuntimeConfig()
    if cfg.provider_type == "fake":
        return FakeStructuredProvider()
    if cfg.provider_type == "openai":
        return OpenAICompatibleProvider(cfg)
    if cfg.provider_type == "azure_openai":
        return AzureOpenAICompatibleProvider(cfg)
    raise NonRetryableModelError(f"unknown provider_type: {cfg.provider_type}")
