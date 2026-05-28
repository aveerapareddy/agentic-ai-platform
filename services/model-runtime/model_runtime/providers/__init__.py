from model_runtime.providers.fake import FakeStructuredProvider
from model_runtime.providers.factory import build_provider


class UnconfiguredHttpProvider:
    """Deprecated stub — configure OpenAI/Azure providers via environment instead."""

    def analyze_incident(self, request):  # noqa: ANN001
        raise RuntimeError(
            "UnconfiguredHttpProvider is deprecated; set MODEL_PROVIDER=openai and API keys.",
        )

    def validate_incident(self, request):  # noqa: ANN001
        raise RuntimeError(
            "UnconfiguredHttpProvider is deprecated; set MODEL_PROVIDER=openai and API keys.",
        )


__all__ = ["FakeStructuredProvider", "UnconfiguredHttpProvider", "build_provider"]
