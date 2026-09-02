"""The ModelRouter: the single seam between Bokken and LLM providers.

Routing classes map cognitive work to models; every dispatch is budget-checked
first and journaled as exactly one ``model.called`` event; structured outputs
are validated at this boundary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, get_args

from pydantic import BaseModel, ValidationError

from bokken.journal import Actor, JournalStore, RoutingClass, Stage, replay
from bokken.models.prompts import render_prompt

FRONTIER_ROUTING_CLASSES: tuple[RoutingClass, ...] = (
    "research",
    "challenge",
    "cognition",
    "generation",
)
# Lane capability: which routing classes a model is allowed to serve. Taken
# from the journal taxonomy so the lane vocabulary cannot drift from it.
ALL_LANES: frozenset[RoutingClass] = frozenset(get_args(RoutingClass))
# CLAUDE.md reserves the extraction-grade model for the extraction class, so
# the delegated sidekick lane is not a cheap dumping ground for it either.
EXTRACTION_ONLY: frozenset[RoutingClass] = frozenset({"extraction"})

DEFAULT_ROUTING: dict[RoutingClass, str] = {
    "research": "claude-fable-5",
    "challenge": "claude-fable-5",
    "cognition": "claude-opus-5",
    "extraction": "claude-haiku-4-5",
    # The sidekick reads and never judges: verbatim corpus spans, UI-step
    # picks. It runs on the cheapest charter-compatible model, not on the
    # frontier model whose price the delegation exists to avoid.
    "sidekick": "claude-sonnet-5",
    "generation": "claude-opus-5",
}

OPENAI_DEFAULT_ROUTING: dict[RoutingClass, str] = {
    "research": "gpt-5",
    "challenge": "gpt-5",
    "cognition": "gpt-5",
    "extraction": "gpt-5-mini",
    "sidekick": "gpt-5-mini",
    "generation": "gpt-5",
}


@dataclass(frozen=True)
class ModelSpec:
    """One allowlisted model: who serves it, what it costs, what it can do."""

    provider: str
    price: tuple[float, float]  # list price per million tokens (input, output)
    lanes: frozenset[RoutingClass] = ALL_LANES  # routing classes it may serve
    reasoning: bool = True  # accepts a reasoning-effort parameter


# The single registry: allowlist, provider map, prices and capability guards
# all derive from it so they cannot drift apart.
MODELS: dict[str, ModelSpec] = {
    "claude-fable-5": ModelSpec("anthropic", (10.0, 50.0)),
    "claude-opus-5": ModelSpec("anthropic", (5.0, 25.0)),
    "claude-sonnet-5": ModelSpec("anthropic", (2.0, 10.0)),
    "claude-opus-4-8": ModelSpec("anthropic", (5.0, 25.0)),
    "claude-opus-4-7": ModelSpec("anthropic", (5.0, 25.0)),
    "claude-sonnet-4-6": ModelSpec("anthropic", (3.0, 15.0)),
    # Extraction only (CLAUDE.md): no effort/adaptive-thinking parameters.
    "claude-haiku-4-5": ModelSpec("anthropic", (1.0, 5.0), lanes=EXTRACTION_ONLY, reasoning=False),
    "gpt-5": ModelSpec("openai", (1.25, 10.0)),
    "gpt-5-mini": ModelSpec("openai", (0.25, 2.0)),
    "gpt-4.1": ModelSpec("openai", (2.0, 8.0), reasoning=False),
    "gpt-4.1-mini": ModelSpec("openai", (0.4, 1.6), reasoning=False),
    "o3": ModelSpec("openai", (2.0, 8.0)),
    "o4-mini": ModelSpec("openai", (1.1, 4.4)),
    "gpt-5.6-luna": ModelSpec("openai", (0.2, 1.2)),
    "gpt-5.6-sol": ModelSpec("openai", (4.0, 20.0)),
    "gpt-5.6-terra": ModelSpec("openai", (2.0, 12.0)),
}
MODEL_ALLOWLIST = frozenset(MODELS)
MODEL_PROVIDERS = {name: spec.provider for name, spec in MODELS.items()}
ANTHROPIC_MODELS = frozenset(n for n, s in MODELS.items() if s.provider == "anthropic")
OPENAI_MODELS = frozenset(n for n, s in MODELS.items() if s.provider == "openai")
PROVIDERS = frozenset({"anthropic", "openai"})
REASONING_EFFORTS = frozenset({"low", "medium", "high"})
DEFAULT_REASONING_EFFORT = "high"


def supports_reasoning(model: str) -> bool:
    spec = MODELS.get(model)
    return spec is not None and spec.reasoning


ROUTER_ACTOR = Actor(kind="agent", name="model-router")

OutcomeStatus = Literal["ok", "refused", "error", "truncated", "budget_exhausted"]


class RoutingConfigError(Exception):
    pass


class ProviderUnavailableError(RoutingConfigError):
    """The session's provider cannot serve: SDK extra not installed or key unset."""


@dataclass(frozen=True)
class ProviderResult:
    text: str
    data: Any | None
    usage: dict[str, int]
    request_id: str | None
    stop_reason: str | None
    model: str


class Provider(Protocol):
    def complete(
        self,
        *,
        model: str,
        prompt_id: str,
        rendered: str,
        schema: type[BaseModel] | None,
        routing_class: RoutingClass,
        stream: bool,
        max_tokens: int,
        web_search: bool = False,
        reasoning_effort: str | None = None,
    ) -> ProviderResult: ...


@dataclass(frozen=True)
class ModelOutcome:
    status: OutcomeStatus
    text: str = ""
    data: Any | None = None
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    request_id: str | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _validate_model_provider(model: str, provider: str) -> ModelSpec:
    spec = MODELS.get(model)
    if spec is None:
        raise RoutingConfigError(f"model {model!r} is not in the allowlist")
    if spec.provider != provider:
        raise RoutingConfigError(f"model {model!r} does not belong to provider {provider!r}")
    return spec


def _validate_class_model(routing_class: RoutingClass, model: str, provider: str) -> None:
    spec = _validate_model_provider(model, provider)
    if routing_class not in spec.lanes:
        raise RoutingConfigError(
            f"model {model!r} may not serve the {routing_class!r} class "
            f"(it serves: {', '.join(sorted(spec.lanes))})"
        )


def _validate_effort(reasoning_effort: str, routing: dict[RoutingClass, str]) -> None:
    if reasoning_effort not in REASONING_EFFORTS:
        raise RoutingConfigError(f"unsupported reasoning effort: {reasoning_effort}")
    for routing_class in FRONTIER_ROUTING_CLASSES:
        model = routing[routing_class]
        if not supports_reasoning(model):
            raise RoutingConfigError(
                f"reasoning effort {reasoning_effort!r} cannot be applied: "
                f"{model!r} ({routing_class}) does not accept a reasoning parameter"
            )


def session_model_config(
    provider: str, model: str | None = None, reasoning_effort: str | None = None
) -> dict[str, Any]:
    """Build validated session config shared by CLI and MCP creation surfaces.

    Every combination is rejected here rather than at first dispatch, so an
    impossible session (haiku on a frontier lane, effort on a model that
    rejects it) never gets created and journaled."""
    if provider not in PROVIDERS:
        raise RoutingConfigError(f"unknown provider: {provider}")
    config: dict[str, Any] = {"provider": provider}
    if model is not None:
        _validate_class_model("cognition", model, provider)
        config["routing"] = {routing_class: model for routing_class in FRONTIER_ROUTING_CLASSES}
    if reasoning_effort is not None:
        _validate_effort(reasoning_effort, resolve_routing(config.get("routing"), provider))
        config["reasoning_effort"] = reasoning_effort
    return config


def resolve_routing(
    overrides: dict[str, str] | None, provider: str = "anthropic"
) -> dict[RoutingClass, str]:
    if provider not in PROVIDERS:
        raise RoutingConfigError(f"unknown provider: {provider}")
    routing: dict[RoutingClass, str] = dict(
        OPENAI_DEFAULT_ROUTING if provider == "openai" else DEFAULT_ROUTING
    )
    for cls, model in (overrides or {}).items():
        if cls not in routing:
            raise RoutingConfigError(f"unknown routing class: {cls}")
        _validate_class_model(cls, model, provider)  # type: ignore[arg-type]
        routing[cls] = model  # type: ignore[index]
    return routing


class ModelRouter:
    """Journal-aware dispatch. Engines never touch the provider SDK directly."""

    def __init__(self, store: JournalStore, provider: Provider) -> None:
        self.store = store
        self.provider = provider
        state = replay(store.events())
        self.provider_name = state.config.get("provider", "anthropic")
        self.routing = resolve_routing(state.config.get("routing"), self.provider_name)
        self.reasoning_effort: str | None = state.config.get("reasoning_effort")

    def actor(
        self, name: str, routing_class: RoutingClass, *, persona_id: str | None = None
    ) -> Actor:
        """Provenance for a journaled contribution: the model routed for its lane."""
        return Actor(
            kind="agent", name=name, model=self.routing[routing_class], persona_id=persona_id
        )

    def invoke(
        self,
        routing_class: RoutingClass,
        prompt_id: str,
        *,
        stage: Stage | None,
        params: dict[str, Any],
        schema: type[BaseModel] | None = None,
        stream: bool = False,
        max_tokens: int = 16000,
        web_search: bool = False,
    ) -> ModelOutcome:
        if web_search and routing_class != "research":
            raise RoutingConfigError("web_search is limited to the research class")
        state = replay(self.store.events())
        budgets = state.config.get("budgets", {})
        class_budget = budgets.get(f"{routing_class}_tokens")
        total_budget = budgets.get("total_tokens")
        if (class_budget is not None and state.tokens_spent(routing_class) >= class_budget) or (
            total_budget is not None and state.tokens_spent() >= total_budget
        ):
            return ModelOutcome(status="budget_exhausted", detail=f"{routing_class} budget spent")

        version, rendered, content_hash = render_prompt(prompt_id, **params)
        model = self.routing[routing_class]
        started = time.monotonic()
        try:
            result = self.provider.complete(
                model=model,
                prompt_id=prompt_id,
                rendered=rendered,
                schema=schema,
                routing_class=routing_class,
                stream=stream,
                max_tokens=max_tokens,
                web_search=web_search,
                reasoning_effort=self.reasoning_effort,
            )
            status: OutcomeStatus = "ok"
            detail = ""
            if result.stop_reason == "refusal":
                status, detail = "refused", "provider safety refusal"
            elif result.stop_reason == "max_tokens":
                status, detail = "truncated", "hit max_tokens"
            data = result.data
            if status == "ok" and schema is not None and not isinstance(data, schema):
                try:
                    data = (
                        schema.model_validate(data)
                        if data is not None
                        else schema.model_validate_json(result.text)
                    )
                except (ValidationError, TypeError, ValueError) as exc:
                    status, detail, data = "error", f"schema validation failed: {exc}", None
        except Exception as exc:  # provider/network failure: journal, then surface
            self._journal_call(
                routing_class,
                model,
                prompt_id,
                version,
                content_hash,
                stage,
                usage={},
                request_id=None,
                status="error",
                duration_ms=int((time.monotonic() - started) * 1000),
                web_search=web_search,
            )
            return ModelOutcome(status="error", model=model, detail=str(exc))

        self._journal_call(
            routing_class,
            model,
            prompt_id,
            version,
            content_hash,
            stage,
            usage=result.usage,
            request_id=result.request_id,
            status=status,
            duration_ms=int((time.monotonic() - started) * 1000),
            web_search=web_search,
            served_model=result.model,
        )
        if status != "ok":
            return ModelOutcome(
                status=status,
                text=result.text,
                usage=result.usage,
                model=result.model or model,
                request_id=result.request_id,
                detail=detail,
            )
        return ModelOutcome(
            status="ok",
            text=result.text,
            data=data,
            usage=result.usage,
            model=result.model or model,
            request_id=result.request_id,
        )

    def _journal_call(
        self,
        routing_class: RoutingClass,
        model: str,
        prompt_id: str,
        version: str,
        content_hash: str,
        stage: Stage | None,
        *,
        usage: dict[str, int],
        request_id: str | None,
        status: str,
        duration_ms: int,
        web_search: bool = False,
        served_model: str | None = None,
    ) -> None:
        # ``model`` is what routing asked for; ``served_model`` is what answered.
        # They differ when a provider-side fallback re-serves a refused call, and
        # cost estimates must price the model that actually ran.
        self.store.append(
            type="model.called",
            stage=stage,
            actor=ROUTER_ACTOR,
            payload={
                "routing_class": routing_class,
                "model": served_model or model,
                "requested_model": model,
                "prompt_id": prompt_id,
                "prompt_version": version,
                "prompt_hash": content_hash,
                "request_id": request_id,
                "usage": usage,
                "status": status,
                "duration_ms": duration_ms,
                "web_search": web_search,
            },
        )
