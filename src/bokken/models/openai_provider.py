"""OpenAI Responses API provider, imported only when an OpenAI call is made."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bokken.journal import RoutingClass
from bokken.models.router import ProviderResult

if TYPE_CHECKING:
    from openai import OpenAI


def _usage_dict(usage: object) -> dict[str, int]:
    details = getattr(usage, "input_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_tokens": getattr(details, "cached_tokens", 0) or 0,
        "cache_write_tokens": 0,
    }


def _stop_reason(response: object) -> str | None:
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        return "max_tokens" if reason == "max_output_tokens" else reason or "incomplete"
    return "end_turn"


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
        kwargs: dict[str, Any] = {
            "model": model,
            "input": rendered,
            "max_output_tokens": max_tokens,
        }
        if web_search:
            kwargs["tools"] = [{"type": "web_search_preview"}]
        if reasoning_effort is not None:
            if reasoning_effort not in {"low", "medium", "high"}:
                raise ValueError(f"unsupported reasoning effort: {reasoning_effort}")
            kwargs["reasoning"] = {"effort": reasoning_effort}

        if schema is not None:
            response = self.client.responses.parse(**kwargs, text_format=schema)
            data = getattr(response, "output_parsed", None)
        else:
            response = self.client.responses.create(**kwargs, stream=stream)
            if stream:
                response = self._final_stream_response(response)
            data = None
        return ProviderResult(
            text=getattr(response, "output_text", "") or "",
            data=data,
            usage=_usage_dict(getattr(response, "usage", None)),
            request_id=getattr(response, "id", None),
            stop_reason=_stop_reason(response),
            model=getattr(response, "model", model) or model,
        )

    @staticmethod
    def _final_stream_response(events: object) -> object:
        final: object | None = None
        for event in events:  # Responses stream ends with response.completed.
            if getattr(event, "type", "") == "response.completed":
                final = getattr(event, "response", None)
        if final is None:
            raise RuntimeError("OpenAI response stream ended without a completed response")
        return final
