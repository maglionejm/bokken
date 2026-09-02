"""The ModelRouter: the single seam between Bokken and LLM providers.

Routing classes map cognitive work to models; every dispatch is budget-checked
first and journaled as exactly one ``model.called`` event; structured outputs
are validated at this boundary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from bokken.journal import Actor, JournalStore, RoutingClass, Stage, replay
from bokken.models.prompts import render_prompt

DEFAULT_ROUTING: dict[RoutingClass, str] = {
    "research": "claude-fable-5",
    "challenge": "claude-fable-5",
    "cognition": "claude-opus-5",
    "extraction": "claude-haiku-4-5",
    "sidekick": "claude-opus-5",
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

ANTHROPIC_MODELS = frozenset(
    {
        "claude-fable-5",
        "claude-opus-5",
        "claude-sonnet-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    }
)
OPENAI_MODELS = frozenset(
    {
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "o3",
        "o4-mini",
        "gpt-5.6-luna",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
    }
)
MODEL_ALLOWLIST = ANTHROPIC_MODELS | OPENAI_MODELS
MODEL_PROVIDERS = {
    **dict.fromkeys(ANTHROPIC_MODELS, "anthropic"),
    **dict.fromkeys(OPENAI_MODELS, "openai"),
}
PROVIDERS = frozenset({"anthropic", "openai"})
FRONTIER_ROUTING_CLASSES: tuple[RoutingClass, ...] = (
    "research",
    "challenge",
    "cognition",
    "generation",
)
REASONING_EFFORTS = frozenset({"low", "medium", "high"})

ROUTER_ACTOR = Actor(kind="agent", name="model-router")

OutcomeStatus = Literal["ok", "refused", "error", "truncated", "budget_exhausted"]


class RoutingConfigError(Exception):
    pass


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


def _validate_model_provider(model: str, provider: str) -> None:
    if model not in MODEL_ALLOWLIST:
        raise RoutingConfigError(f"model {model!r} is not in the allowlist")
    if MODEL_PROVIDERS[model] != provider:
        raise RoutingConfigError(f"model {model!r} does not belong to provider {provider!r}")


def session_model_config(
    provider: str, model: str | None = None, reasoning_effort: str | None = None
) -> dict[str, Any]:
    """Build validated session config shared by CLI and MCP creation surfaces."""
    if provider not in PROVIDERS:
        raise RoutingConfigError(f"unknown provider: {provider}")
    config: dict[str, Any] = {"provider": provider}
    if model is not None:
        _validate_model_provider(model, provider)
        config["routing"] = {routing_class: model for routing_class in FRONTIER_ROUTING_CLASSES}
    if reasoning_effort is not None:
        if reasoning_effort not in REASONING_EFFORTS:
            raise RoutingConfigError(f"unsupported reasoning effort: {reasoning_effort}")
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
        _validate_model_provider(model, provider)
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
                **(
                    {"reasoning_effort": state.config["reasoning_effort"]}
                    if state.config.get("reasoning_effort") is not None
                    else {}
                ),
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
                    data = schema.model_validate(data if data is not None else result.text)
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
        )
        if status != "ok":
            return ModelOutcome(
                status=status,
                text=result.text,
                usage=result.usage,
                model=model,
                request_id=result.request_id,
                detail=detail,
            )
        return ModelOutcome(
            status="ok",
            text=result.text,
            data=data,
            usage=result.usage,
            model=model,
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
    ) -> None:
        self.store.append(
            type="model.called",
            stage=stage,
            actor=ROUTER_ACTOR,
            payload={
                "routing_class": routing_class,
                "model": model,
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
