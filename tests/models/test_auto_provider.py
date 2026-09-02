"""AutoProvider must refuse up front, not journal config errors as model failures."""

import builtins

import pytest

from bokken.models import AutoProvider, ProviderUnavailableError, RoutingConfigError


def test_unknown_model_has_no_provider() -> None:
    with pytest.raises(RoutingConfigError, match="no provider registered"):
        AutoProvider().complete(model="not-a-model")


def test_missing_openai_extra_is_a_configuration_refusal(monkeypatch) -> None:
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__("sys").modules, "bokken.models.openai_provider", raising=False)
    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ProviderUnavailableError, match="install the 'openai' extra"):
        AutoProvider().preflight(["gpt-5"])


def test_client_construction_failure_is_a_configuration_refusal(monkeypatch) -> None:
    import bokken.models.openai_provider as mod

    def explode(self, client=None):
        raise RuntimeError("OPENAI_API_KEY is not set")

    monkeypatch.setattr(mod.OpenAIProvider, "__init__", explode)
    with pytest.raises(ProviderUnavailableError, match="API key"):
        AutoProvider().preflight(["gpt-5"])
