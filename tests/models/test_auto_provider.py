"""AutoProvider must refuse up front, not journal config errors as model failures."""

import builtins
import sys
from types import ModuleType

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

    monkeypatch.delitem(sys.modules, "openai", raising=False)

    monkeypatch.delitem(sys.modules, "bokken.models.openai_provider", raising=False)
    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ProviderUnavailableError, match="install the 'openai' extra"):
        AutoProvider().preflight(["gpt-5"])


def test_client_construction_failure_is_a_configuration_refusal(monkeypatch) -> None:
    """A constructible SDK whose client refuses (no API key) is still a config error.

    The stub module keeps this hermetic: the core install has no ``openai``
    extra, and without the stub the import would fail first and this would
    assert the wrong refusal.
    """
    stub = ModuleType("openai")

    class _OpenAI:
        def __init__(self, *a, **kw):
            raise RuntimeError("The api_key client option must be set")

    stub.OpenAI = _OpenAI
    monkeypatch.setitem(sys.modules, "openai", stub)
    monkeypatch.delitem(sys.modules, "bokken.models.openai_provider", raising=False)
    with pytest.raises(ProviderUnavailableError, match="API key"):
        AutoProvider().preflight(["gpt-5"])
