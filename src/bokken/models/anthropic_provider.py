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
    ) -> ProviderResult:
        messages = [{"role": "user", "content": rendered}]
        kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if routing_class in ("cognition", "generation"):
            kwargs["thinking"] = {"type": "adaptive"}

        if schema is not None:
            response = self.client.messages.parse(**kwargs, output_format=schema)
            return ProviderResult(
                text=_text_of(response),
                data=response.parsed_output,
                usage=_usage_dict(response.usage),
                request_id=getattr(response, "_request_id", None),
                stop_reason=response.stop_reason,
                model=response.model,
            )

        if stream:
            with self.client.messages.stream(**kwargs) as message_stream:
                response = message_stream.get_final_message()
        else:
            response = self.client.messages.create(**kwargs)
        return ProviderResult(
            text=_text_of(response) if response.stop_reason != "refusal" else "",
            data=None,
            usage=_usage_dict(response.usage),
            request_id=getattr(response, "_request_id", None),
            stop_reason=response.stop_reason,
            model=response.model,
        )
