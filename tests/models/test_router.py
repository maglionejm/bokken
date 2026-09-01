from pathlib import Path

import pytest
from pydantic import BaseModel

from bokken.journal import JournalStore, replay
from bokken.models import ModelRouter, ProviderResult, RoutingConfigError, resolve_routing
from tests.journal.conftest import SYSTEM, created_payload


class Echo(BaseModel):
    value: str


class OneShotProvider:
    def __init__(self, result: ProviderResult | Exception) -> None:
        self.result = result
        self.calls = 0

    def complete(self, **kw):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def ok_result(data=None, text="hi", stop_reason="end_turn") -> ProviderResult:
    return ProviderResult(
        text=text,
        data=data,
        usage={"input_tokens": 100, "output_tokens": 40},
        request_id="req-1",
        stop_reason=stop_reason,
        model="claude-opus-4-8",
    )


@pytest.fixture
def store(tmp_path: Path):
    with JournalStore.open(tmp_path / "s") as s:
        s.append(type="session.created", stage="intake", actor=SYSTEM, payload=created_payload())
        yield s


def test_routing_defaults_and_overrides() -> None:
    routing = resolve_routing(None)
    assert routing["research"] == "claude-fable-5"
    assert routing["challenge"] == "claude-fable-5"
    assert routing["cognition"] == "claude-fable-5"
    assert routing["generation"] == "claude-fable-5"
    assert routing["extraction"] == "claude-haiku-4-5"
    assert resolve_routing({"cognition": "claude-sonnet-4-6"})["cognition"] == "claude-sonnet-4-6"
    with pytest.raises(RoutingConfigError, match="allowlist"):
        resolve_routing({"cognition": "gpt-5"})
    with pytest.raises(RoutingConfigError, match="unknown routing class"):
        resolve_routing({"vibes": "claude-haiku-4-5"})


def test_invocation_is_journaled_with_prompt_version_and_usage(store) -> None:
    router = ModelRouter(store, OneShotProvider(ok_result(data=Echo(value="x"))))
    outcome = router.invoke(
        "extraction",
        "ideate/novelty",
        stage="ideate",
        params={"clusters": "a", "option": "b"},
        schema=Echo,
    )
    assert outcome.ok and outcome.data.value == "x"
    events = [e for e in store.events() if e.type == "model.called"]
    assert len(events) == 1
    payload = events[0].payload
    assert payload["routing_class"] == "extraction"
    assert payload["model"] == "claude-haiku-4-5"
    assert payload["prompt_id"] == "ideate/novelty"
    assert payload["prompt_version"] == "v1"
    assert len(payload["prompt_hash"]) == 64
    assert payload["usage"]["input_tokens"] == 100
    assert payload["status"] == "ok"
    state = replay(store.events())
    assert state.tokens_spent("extraction") == 140


def test_budget_exhaustion_refuses_dispatch_without_provider_call(tmp_path: Path) -> None:
    with JournalStore.open(tmp_path / "s") as store:
        payload = created_payload()
        payload["config"] = {"budgets": {"total_tokens": 10}}
        store.append(type="session.created", stage="intake", actor=SYSTEM, payload=payload)
        provider = OneShotProvider(ok_result())
        router = ModelRouter(store, provider)
        router.invoke("cognition", "define/select", stage="define", params={"candidates": "x"})
        outcome = router.invoke(
            "cognition", "define/select", stage="define", params={"candidates": "x"}
        )
        assert outcome.status == "budget_exhausted"
        assert provider.calls == 1
        assert len([e for e in store.events() if e.type == "model.called"]) == 1


def test_refusal_is_journaled_and_typed(store) -> None:
    router = ModelRouter(store, OneShotProvider(ok_result(stop_reason="refusal", text="")))
    outcome = router.invoke(
        "cognition", "define/select", stage="define", params={"candidates": "x"}
    )
    assert outcome.status == "refused"
    event = next(e for e in store.events() if e.type == "model.called")
    assert event.payload["status"] == "refused"


def test_schema_violation_is_contained(store) -> None:
    router = ModelRouter(store, OneShotProvider(ok_result(data=None, text="not json")))
    outcome = router.invoke(
        "cognition", "define/select", stage="define", params={"candidates": "x"}, schema=Echo
    )
    assert outcome.status == "error"
    assert outcome.data is None
    event = next(e for e in store.events() if e.type == "model.called")
    assert event.payload["status"] == "error"


def test_provider_exception_is_journaled_as_error(store) -> None:
    router = ModelRouter(store, OneShotProvider(RuntimeError("network down")))
    outcome = router.invoke(
        "cognition", "define/select", stage="define", params={"candidates": "x"}
    )
    assert outcome.status == "error" and "network down" in outcome.detail
    event = next(e for e in store.events() if e.type == "model.called")
    assert event.payload["status"] == "error"


def test_prompt_registry_carries_the_quality_contract_and_hill() -> None:
    from bokken.models.prompts import PROMPTS, QUALITY_CONTRACT, render_prompt

    assert QUALITY_CONTRACT in PROMPTS["test/recommend"][1]
    _, rendered, _ = render_prompt(
        "prototype/artifact",
        kind="concept_one_pager",
        concept="c",
        problem_statement="p",
        assumptions="a",
    )
    assert "WHO" in rendered and "We believe" in rendered
    _, rendered, _ = render_prompt("empathize/outcomes", brief="b", evidence="(none)")
    assert "Ulwick" in rendered or "Jobs-to-be-Done" in rendered
