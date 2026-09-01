"""Request-shape contract per model family, verified against a stub client."""

from types import SimpleNamespace

from pydantic import BaseModel

from bokken.models.anthropic_provider import AnthropicProvider


class Echo(BaseModel):
    value: str


def response(model: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[],
        parsed_output=Echo(value="x"),
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        _request_id="req-1",
        stop_reason="end_turn",
        model=model,
    )


class Surface:
    def __init__(self, name: str, log: dict) -> None:
        self.name, self.log = name, log

    def parse(self, **kwargs):
        self.log[self.name] = kwargs
        return response(kwargs["model"])

    create = parse


def make_client(log: dict):
    return SimpleNamespace(
        messages=Surface("plain", log),
        beta=SimpleNamespace(messages=Surface("beta", log)),
    )


def call(routing_class: str, model: str) -> dict:
    log: dict = {}
    provider = AnthropicProvider(client=make_client(log))
    provider.complete(
        model=model,
        prompt_id="x/y",
        rendered="hi",
        schema=Echo,
        routing_class=routing_class,  # type: ignore[arg-type]
        stream=False,
        max_tokens=100,
    )
    return log


def test_fable_requests_omit_thinking_and_opt_into_fallback() -> None:
    log = call("research", "claude-fable-5")
    kwargs = log["beta"]  # fable goes through the beta surface
    assert "thinking" not in kwargs
    assert kwargs["output_config"] == {"effort": "high"}
    assert kwargs["betas"] == ["server-side-fallback-2026-06-01"]
    assert kwargs["fallbacks"] == [{"model": "claude-opus-4-8"}]


def test_challenge_class_matches_research_shape() -> None:
    kwargs = call("challenge", "claude-fable-5")["beta"]
    assert "thinking" not in kwargs and kwargs["output_config"] == {"effort": "high"}


def test_opus_requests_use_adaptive_thinking_at_high_effort() -> None:
    kwargs = call("cognition", "claude-opus-5")["plain"]
    assert kwargs["thinking"] == {"type": "adaptive"}
    assert kwargs["output_config"] == {"effort": "high"}
    assert "fallbacks" not in kwargs and "betas" not in kwargs


def test_extraction_requests_stay_minimal() -> None:
    kwargs = call("extraction", "claude-haiku-4-5")["plain"]
    assert "thinking" not in kwargs and "output_config" not in kwargs


def test_cache_split_marks_the_prefix_block() -> None:
    from bokken.models.prompts import CACHE_SPLIT

    log: dict = {}
    provider = AnthropicProvider(client=make_client(log))
    provider.complete(
        model="claude-opus-5",
        prompt_id="x/y",
        rendered=f"BIG CORPUS{CACHE_SPLIT}the question",
        schema=Echo,
        routing_class="sidekick",  # type: ignore[arg-type]
        stream=False,
        max_tokens=100,
    )
    content = log["plain"]["messages"][0]["content"]
    assert content[0]["cache_control"] == {"type": "ephemeral"}
    assert content[0]["text"] == "BIG CORPUS" and content[1]["text"] == "the question"
