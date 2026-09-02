from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from bokken.models.openai_provider import OpenAIProvider


class Echo(BaseModel):
    value: str


def response() -> SimpleNamespace:
    return SimpleNamespace(
        output_text='{"value":"x"}',
        output_parsed=Echo(value="x"),
        usage=SimpleNamespace(
            input_tokens=3,
            output_tokens=2,
            input_tokens_details=SimpleNamespace(cached_tokens=1),
        ),
        id="resp-1",
        status="completed",
        model="gpt-5",
    )


class Responses:
    def __init__(self):
        self.log = {}

    def parse(self, **kwargs):
        self.log["parse"] = kwargs
        return response()

    def create(self, **kwargs):
        self.log["create"] = kwargs
        return response()


def test_structured_request_uses_responses_parse_and_normalizes_result():
    responses = Responses()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    result = provider.complete(
        model="gpt-5",
        prompt_id="x/y",
        rendered="hello",
        schema=Echo,
        routing_class="cognition",
        stream=False,
        max_tokens=100,
        reasoning_effort="high",
    )
    assert result.data == Echo(value="x")
    assert result.request_id == "resp-1"
    assert result.usage["input_tokens"] == 2
    assert result.usage["cache_read_tokens"] == 1
    assert responses.log["parse"]["text_format"] is Echo
    assert responses.log["parse"]["reasoning"] == {"effort": "high"}


def test_plain_request_can_enable_web_search():
    responses = Responses()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    provider.complete(
        model="gpt-5",
        prompt_id="x/y",
        rendered="hello",
        schema=None,
        routing_class="research",
        stream=False,
        max_tokens=100,
        web_search=True,
    )
    assert responses.log["create"]["tools"] == [{"type": "web_search"}]


def test_cache_marker_is_removed_without_reordering_prompt():
    from bokken.models.prompts import CACHE_SPLIT

    responses = Responses()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    provider.complete(
        model="gpt-5-mini",
        prompt_id="x/y",
        rendered=f"BIG CORPUS{CACHE_SPLIT}the question",
        schema=None,
        routing_class="sidekick",
        stream=False,
        max_tokens=100,
    )
    rendered = responses.log["create"]["input"]
    assert rendered == "BIG CORPUS\nthe question"
    assert CACHE_SPLIT.strip() not in rendered


def test_reasoning_effort_is_skipped_for_economy_lanes_and_plain_models():
    responses = Responses()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    provider.complete(
        model="gpt-5-mini",
        prompt_id="x/y",
        rendered="hello",
        schema=None,
        routing_class="sidekick",
        stream=False,
        max_tokens=100,
        reasoning_effort="high",
    )
    assert "reasoning" not in responses.log["create"]

    provider.complete(
        model="gpt-4.1",
        prompt_id="x/y",
        rendered="hello",
        schema=None,
        routing_class="cognition",
        stream=False,
        max_tokens=100,
        reasoning_effort="high",
    )
    assert "reasoning" not in responses.log["create"]


def test_truncated_stream_returns_the_incomplete_response_with_usage():
    incomplete = SimpleNamespace(
        output_text="half an answer",
        usage=SimpleNamespace(
            input_tokens=10, output_tokens=64, input_tokens_details=SimpleNamespace(cached_tokens=0)
        ),
        id="resp-2",
        status="incomplete",
        incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        model="gpt-5",
    )

    class Streaming:
        def create(self, **kwargs):
            return [SimpleNamespace(type="response.incomplete", response=incomplete)]

    provider = OpenAIProvider(client=SimpleNamespace(responses=Streaming()))
    result = provider.complete(
        model="gpt-5",
        prompt_id="x/y",
        rendered="hello",
        schema=None,
        routing_class="generation",
        stream=True,
        max_tokens=64,
    )
    assert result.stop_reason == "max_tokens"
    assert result.text == "half an answer"
    assert result.usage["output_tokens"] == 64


def test_refusal_is_reported_as_a_refusal_not_an_empty_answer():
    refused = SimpleNamespace(
        output_text="",
        output_parsed=None,
        output=[
            SimpleNamespace(
                type="message", content=[SimpleNamespace(type="refusal", refusal="cannot help")]
            )
        ],
        usage=SimpleNamespace(
            input_tokens=5, output_tokens=1, input_tokens_details=SimpleNamespace(cached_tokens=0)
        ),
        id="resp-3",
        status="completed",
        model="gpt-5",
    )

    class Refusing:
        def parse(self, **kwargs):
            return refused

    provider = OpenAIProvider(client=SimpleNamespace(responses=Refusing()))
    result = provider.complete(
        model="gpt-5",
        prompt_id="x/y",
        rendered="hello",
        schema=Echo,
        routing_class="challenge",
        stream=False,
        max_tokens=100,
    )
    assert result.stop_reason == "refusal"
    assert result.data is None


def test_failed_response_raises_so_the_router_journals_an_error():
    failed = SimpleNamespace(
        output_text="",
        usage=None,
        id="resp-4",
        status="failed",
        error=SimpleNamespace(message="upstream exploded"),
        model="gpt-5",
    )

    class Failing:
        def create(self, **kwargs):
            return failed

    provider = OpenAIProvider(client=SimpleNamespace(responses=Failing()))
    with pytest.raises(RuntimeError, match="upstream exploded"):
        provider.complete(
            model="gpt-5",
            prompt_id="x/y",
            rendered="hello",
            schema=None,
            routing_class="research",
            stream=False,
            max_tokens=100,
        )


def test_structured_generation_streams_when_asked():
    class Stream:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_response(self):
            return response()

    class Streaming:
        def __init__(self):
            self.streamed = None

        def stream(self, **kwargs):
            self.streamed = kwargs
            return Stream(**kwargs)

    responses = Streaming()
    provider = OpenAIProvider(client=SimpleNamespace(responses=responses))
    result = provider.complete(
        model="gpt-5",
        prompt_id="x/y",
        rendered="hello",
        schema=Echo,
        routing_class="generation",
        stream=True,
        max_tokens=48000,
    )
    assert responses.streamed["text_format"] is Echo
    assert result.data == Echo(value="x")
