"""Anthropic SDK provider: adaptive thinking for cognition, streaming for generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from bokken.journal import RoutingClass
from bokken.models.router import ProviderResult

if TYPE_CHECKING:
    import anthropic


def _usage_dict(usage: object) -> dict[str, int]:
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }


def _text_of(message: object) -> str:
    return "".join(block.text for block in getattr(message, "content", []) if block.type == "text")


class AnthropicProvider:
    """Requires ANTHROPIC_API_KEY. Constructed lazily so offline tests never import-fail."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        if client is None:
            import anthropic as _anthropic

            client = _anthropic.Anthropic()
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
    ) -> ProviderResult:
        messages = [{"role": "user", "content": rendered}]
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
        is_fable = model.startswith("claude-fable")
        if routing_class in ("research", "challenge", "cognition", "generation"):
            kwargs["output_config"] = {"effort": "high"}
            if not is_fable:
                # Fable's thinking is always on and rejects the parameter.
                kwargs["thinking"] = {"type": "adaptive"}
        if is_fable:
            # Safety-classifier declines are re-served by Opus inside the same call.
            kwargs["betas"] = ["server-side-fallback-2026-06-01"]
            kwargs["fallbacks"] = [{"model": "claude-opus-4-8"}]

        if web_search:
            kwargs["tools"] = [
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 12}
            ]
        surface = self.client.beta.messages if is_fable else self.client.messages
        if schema is not None:
            response = surface.parse(**kwargs, output_format=schema)
            return ProviderResult(
                text=_text_of(response),
                data=response.parsed_output,
                usage=_usage_dict(response.usage),
                request_id=getattr(response, "_request_id", None),
                stop_reason=response.stop_reason,
                model=response.model,
            )

        if stream:
            with surface.stream(**kwargs) as message_stream:
                response = message_stream.get_final_message()
        else:
            response = surface.create(**kwargs)
        return ProviderResult(
            text=_text_of(response) if response.stop_reason != "refusal" else "",
            data=None,
            usage=_usage_dict(response.usage),
            request_id=getattr(response, "_request_id", None),
            stop_reason=response.stop_reason,
            model=response.model,
        )
