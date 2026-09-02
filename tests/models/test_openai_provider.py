from types import SimpleNamespace

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
