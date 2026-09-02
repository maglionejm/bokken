"""Lazy provider selection based on the routed model family."""

from __future__ import annotations

from typing import Any

from bokken.models.router import (
    MODEL_PROVIDERS,
    Provider,
    ProviderResult,
    ProviderUnavailableError,
    RoutingConfigError,
)


class AutoProvider:
    """Load only the SDK needed by the selected model.

    Construction failures (missing optional extra, missing API key) surface as
    ``ProviderUnavailableError`` so the run refuses instead of journaling a
    configuration mistake as a model failure on every call.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def _provider_for(self, provider: str) -> Provider:
        existing = self._providers.get(provider)
        if existing is not None:
            return existing
        try:
            if provider == "openai":
                from bokken.models.openai_provider import OpenAIProvider

                built: Provider = OpenAIProvider()
            else:
                from bokken.models.anthropic_provider import AnthropicProvider

                built = AnthropicProvider()
        except ImportError as exc:
            extra = " (install the 'openai' extra)" if provider == "openai" else ""
            raise ProviderUnavailableError(f"{provider} SDK is unavailable{extra}: {exc}") from exc
        except Exception as exc:
            raise ProviderUnavailableError(
                f"{provider} client could not be created (is the API key set?): {exc}"
            ) from exc
        self._providers[provider] = built
        return built

    def complete(self, *, model: str, **kwargs: Any) -> ProviderResult:
        provider = MODEL_PROVIDERS.get(model)
        if provider is None:
            raise RoutingConfigError(f"no provider registered for model {model!r}")
        return self._provider_for(provider).complete(model=model, **kwargs)

    def preflight(self, models: list[str]) -> None:
        """Build every client a session will need, before any journal writes."""
        for provider in {MODEL_PROVIDERS[m] for m in models if m in MODEL_PROVIDERS}:
            self._provider_for(provider)
