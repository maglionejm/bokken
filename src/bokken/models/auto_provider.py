"""Lazy provider selection based on the routed model family."""

from __future__ import annotations

from typing import Any

from bokken.models.router import MODEL_PROVIDERS, Provider, ProviderResult, RoutingConfigError


class AutoProvider:
    """Load only the SDK needed by the selected model."""

    def __init__(self) -> None:
        self._anthropic: Provider | None = None
        self._openai: Provider | None = None

    def complete(self, *, model: str, **kwargs: Any) -> ProviderResult:
        provider = MODEL_PROVIDERS.get(model)
        if provider is None:
            raise RoutingConfigError(f"no provider registered for model {model!r}")
        if provider == "openai":
            if self._openai is None:
                from bokken.models.openai_provider import OpenAIProvider

                self._openai = OpenAIProvider()
            return self._openai.complete(model=model, **kwargs)
        if self._anthropic is None:
            from bokken.models.anthropic_provider import AnthropicProvider

            self._anthropic = AnthropicProvider()
        return self._anthropic.complete(model=model, **kwargs)
