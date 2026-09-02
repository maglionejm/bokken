"""Stage engines: what each Design Thinking stage does when it runs."""

from collections.abc import Callable

from bokken.journal import JournalStore, Stage
from bokken.models.router import ModelRouter
from bokken.orchestrator import StageEngine
from bokken.stages.base import RouterFactory, StageError
from bokken.stages.define import DefineEngine
from bokken.stages.empathize import EmpathizeEngine
from bokken.stages.ideate import IdeateEngine
from bokken.stages.persona_gen import RouterTurnGenerator
from bokken.stages.prototype import PrototypeEngine
from bokken.stages.testing import TestEngine


def engine_suite(router_factory: RouterFactory) -> dict[Stage, StageEngine]:
    """The five production engines wired to a router factory."""
    return {
        "empathize": EmpathizeEngine(router_factory),
        "define": DefineEngine(router_factory),
        "ideate": IdeateEngine(router_factory),
        "prototype": PrototypeEngine(router_factory),
        "test": TestEngine(router_factory),
    }


def anthropic_router_factory() -> Callable[[JournalStore], ModelRouter]:
    """Router factory backed by the real Anthropic provider."""
    from bokken.models.anthropic_provider import AnthropicProvider

    provider = AnthropicProvider()
    return lambda store: ModelRouter(store, provider)


def provider_router_factory() -> Callable[[JournalStore], ModelRouter]:
    """Router factory selecting Anthropic or OpenAI from session routing.

    Clients are built up front so a missing SDK extra or API key refuses the
    run instead of being journaled as a model failure on every call."""
    from bokken.models.auto_provider import AutoProvider

    provider = AutoProvider()

    def build(store: JournalStore) -> ModelRouter:
        router = ModelRouter(store, provider)
        provider.preflight(list(router.routing.values()))
        return router

    return build


__all__ = [
    "DefineEngine",
    "EmpathizeEngine",
    "IdeateEngine",
    "PrototypeEngine",
    "RouterFactory",
    "RouterTurnGenerator",
    "StageError",
    "TestEngine",
    "anthropic_router_factory",
    "engine_suite",
    "provider_router_factory",
]
