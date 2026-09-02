"""OpenAI Responses API provider, imported only when an OpenAI call is made."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bokken.journal import RoutingClass
from bokken.models.router import (
    DEFAULT_REASONING_EFFORT,
    FRONTIER_ROUTING_CLASSES,
    REASONING_EFFORTS,
    ProviderResult,
    supports_reasoning,
)

if TYPE_CHECKING:
    from openai import OpenAI

# Responses streams end with exactly one of these; each carries the final response.
_TERMINAL_EVENTS = {"response.completed", "response.incomplete", "response.failed"}


def _usage_dict(usage: object) -> dict[str, int]:
    details = getattr(usage, "input_tokens_details", None)
    total_input = getattr(usage, "input_tokens", 0) or 0
    cached_input = getattr(details, "cached_tokens", 0) or 0
    # OpenAI includes cached tokens in input_tokens; Bokken's normalized usage
    # buckets are disjoint so budgets and cost estimates do not double-count.
    return {
        "input_tokens": max(total_input - cached_input, 0),
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_tokens": cached_input,
        "cache_write_tokens": 0,
    }


def _refused(response: object) -> bool:
    """A refusal is a message item whose content is a ``refusal`` part."""
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                return True
    return False


def _stop_reason(response: object) -> str | None:
    if _refused(response):
        return "refusal"
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        return "max_tokens" if reason == "max_output_tokens" else reason or "incomplete"
    return "end_turn"


def _raise_if_failed(response: object) -> None:
    status = getattr(response, "status", None)
    if status in ("failed", "cancelled"):
        error = getattr(response, "error", None)
        message = getattr(error, "message", None) or status
        raise RuntimeError(f"OpenAI response {status}: {message}")


class OpenAIProvider:
    """Requires the optional ``openai`` extra and ``OPENAI_API_KEY``."""

    def __init__(self, client: OpenAI | None = None) -> None:
        if client is None:
            from openai import OpenAI as _OpenAI

            client = _OpenAI()
        self.client = client

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
    ) -> ProviderResult:
        from bokken.models.prompts import split_cache_marker

        # Anthropic uses the marker for explicit cache blocks; OpenAI caches
        # shared prefixes implicitly, so send the same text with the marker gone.
        kwargs: dict[str, Any] = {
            "model": model,
            "input": "".join(split_cache_marker(rendered)),
            "max_output_tokens": max_tokens,
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        # Effort applies to the frontier lanes only (parity with the Anthropic
        # adapter) and never to models that reject the parameter.
        if routing_class in FRONTIER_ROUTING_CLASSES and supports_reasoning(model):
            effort = reasoning_effort or DEFAULT_REASONING_EFFORT
            if effort not in REASONING_EFFORTS:
                raise ValueError(f"unsupported reasoning effort: {effort}")
            kwargs["reasoning"] = {"effort": effort}

        data = None
        if schema is not None and stream:
            with self.client.responses.stream(**kwargs, text_format=schema) as events:
                response = events.get_final_response()
            data = getattr(response, "output_parsed", None)
        elif schema is not None:
            response = self.client.responses.parse(**kwargs, text_format=schema)
            data = getattr(response, "output_parsed", None)
        elif stream:
            response = self._final_stream_response(
                self.client.responses.create(**kwargs, stream=True)
            )
        else:
            response = self.client.responses.create(**kwargs)
        _raise_if_failed(response)
        stop_reason = _stop_reason(response)
        return ProviderResult(
            text=(getattr(response, "output_text", "") or "") if stop_reason != "refusal" else "",
            data=data if stop_reason != "refusal" else None,
            usage=_usage_dict(getattr(response, "usage", None)),
            request_id=getattr(response, "id", None),
            stop_reason=stop_reason,
            model=getattr(response, "model", model) or model,
        )

    @staticmethod
    def _final_stream_response(events: object) -> object:
        final: object | None = None
        for event in events:
            if getattr(event, "type", "") in _TERMINAL_EVENTS:
                final = getattr(event, "response", None)
        if final is None:
            raise RuntimeError("OpenAI response stream ended without a terminal response event")
        return final
