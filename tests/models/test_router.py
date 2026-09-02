from pathlib import Path

import pytest
from pydantic import BaseModel

from bokken.journal import JournalStore, replay
from bokken.models import (
    ModelRouter,
    ProviderResult,
    RoutingConfigError,
    resolve_routing,
    session_model_config,
)
from tests.journal.conftest import SYSTEM, created_payload


class Echo(BaseModel):
    value: str


class OneShotProvider:
    def __init__(self, result: ProviderResult | Exception) -> None:
        self.result = result
        self.calls = 0

    def complete(self, **kw):  # accepts web_search etc.
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class RecordingProvider(OneShotProvider):
    """Keeps the last call's kwargs so request shape can be asserted."""

    def complete(self, **kw):
        self.kwargs = kw
        return super().complete(**kw)


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
    assert routing["cognition"] == "claude-opus-5"
    assert routing["generation"] == "claude-opus-5"
    assert routing["extraction"] == "claude-haiku-4-5"
    assert resolve_routing({"cognition": "claude-sonnet-4-6"})["cognition"] == "claude-sonnet-4-6"
    assert resolve_routing({"cognition": "gpt-5"}, provider="openai")["cognition"] == "gpt-5"
    openai_routing = resolve_routing(None, provider="openai")
    assert openai_routing["extraction"] == "gpt-5-mini"
    assert openai_routing["sidekick"] == "gpt-5-mini"
    with pytest.raises(RoutingConfigError, match="allowlist"):
        resolve_routing({"cognition": "not-a-model"})
    with pytest.raises(RoutingConfigError, match="does not belong"):
        resolve_routing({"cognition": "claude-opus-5"}, provider="openai")
    with pytest.raises(RoutingConfigError, match="unknown routing class"):
        resolve_routing({"vibes": "claude-haiku-4-5"})


def test_frontier_override_preserves_economy_lanes() -> None:
    config = session_model_config("openai", "gpt-5.6-luna", "high")
    assert set(config["routing"]) == {"research", "challenge", "cognition", "generation"}
    routing = resolve_routing(config["routing"], provider="openai")
    assert routing["sidekick"] == "gpt-5-mini"
    assert routing["extraction"] == "gpt-5-mini"
    assert config["reasoning_effort"] == "high"


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
    # The provider answered on a different model (server-side fallback shape):
    # the journal records who served it and what routing asked for.
    assert payload["model"] == "claude-opus-4-8"
    assert payload["requested_model"] == "claude-haiku-4-5"
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
        design_tokens="(n/a)",
        problem_statement="p",
        assumptions="a",
    )
    assert "WHO" in rendered and "We believe" in rendered
    _, rendered, _ = render_prompt("empathize/outcomes", brief="b", evidence="(none)")
    assert "Ulwick" in rendered or "Jobs-to-be-Done" in rendered


def test_extraction_grade_models_are_refused_on_frontier_lanes() -> None:
    with pytest.raises(RoutingConfigError, match="may not serve"):
        session_model_config("anthropic", "claude-haiku-4-5")
    with pytest.raises(RoutingConfigError, match="may not serve"):
        resolve_routing({"cognition": "claude-haiku-4-5"})
    # The extraction lane itself still accepts it.
    assert resolve_routing({"extraction": "claude-haiku-4-5"})["extraction"] == "claude-haiku-4-5"


def test_effort_is_refused_for_models_that_reject_the_parameter() -> None:
    with pytest.raises(RoutingConfigError, match="does not accept a reasoning parameter"):
        session_model_config("openai", "gpt-4.1", "high")
    assert session_model_config("openai", "gpt-5", "low")["reasoning_effort"] == "low"


def test_configured_effort_reaches_the_provider(tmp_path: Path) -> None:
    with JournalStore.open(tmp_path / "s") as store:
        payload = created_payload()
        payload["config"] = session_model_config("anthropic", reasoning_effort="low")
        store.append(type="session.created", stage="intake", actor=SYSTEM, payload=payload)
        provider = RecordingProvider(ok_result())
        ModelRouter(store, provider).invoke(
            "cognition", "define/select", stage="define", params={"candidates": "x"}
        )
        assert provider.kwargs["reasoning_effort"] == "low"


def test_actor_provenance_follows_session_routing(tmp_path: Path) -> None:
    with JournalStore.open(tmp_path / "s") as store:
        payload = created_payload()
        payload["config"] = session_model_config("openai")
        store.append(type="session.created", stage="intake", actor=SYSTEM, payload=payload)
        router = ModelRouter(store, RecordingProvider(ok_result()))
        assert router.actor("facilitator", "cognition").model == "gpt-5"
        assert router.actor("novelty", "extraction").model == "gpt-5-mini"


def test_every_allowlisted_model_has_a_list_price() -> None:
    from bokken.models.router import MODEL_ALLOWLIST, MODELS
    from bokken.report.context import PRICE_PER_MTOK

    assert set(PRICE_PER_MTOK) == set(MODEL_ALLOWLIST)
    for name, spec in MODELS.items():
        assert PRICE_PER_MTOK[name] == spec.price


def test_persona_turn_caches_one_corpus_prefix_across_the_panel() -> None:
    """The inversion this guards against: a persona named above the corpus gives
    every turn its own prefix, so the corpus is never read back from cache."""
    from bokken.models.prompts import render_prompt, split_cache_marker

    corpus = "[source abcdef123456 (code) L1-L4]\nshuttle arrivals drift by 9 minutes\n"
    question = "tell me about the last time the shuttle was late"
    prefixes, suffixes = set(), set()
    for persona in ('{"name": "Carmen"}', '{"name": "Diego"}', '{"name": "Rosa"}'):
        _, rendered, _ = render_prompt(
            "empathize/persona_turn", persona=persona, context=corpus, question=question
        )
        prefix, suffix = split_cache_marker(rendered)
        prefixes.add(prefix)
        suffixes.add(suffix)
        # The marker splits shared material from varying material, not the reverse.
        assert corpus in prefix and persona not in prefix and question not in prefix
        assert persona in suffix and question in suffix
    assert len(prefixes) == 1, "the cacheable prefix must be byte-identical per persona"
    assert len(suffixes) == 3


def test_cache_split_keeps_shared_material_ahead_of_per_call_material() -> None:
    """Every marked prompt: shared params before the split, varying ones after."""
    from bokken.models.prompts import CACHE_SPLIT, render_prompt, split_cache_marker

    cases = {
        "sidekick/context_query": ({"context": "CORPUS"}, {"question": "QUESTION"}),
        "empathize/persona_turn": (
            {"context": "CORPUS"},
            {"persona": "PERSONA", "question": "QUESTION"},
        ),
        "ideate/converge": (
            {"problem_statement": "PROBLEM", "criteria": "CRITERIA", "options": "OPTIONS"},
            {"participant": "PARTICIPANT", "lens": "LENS"},
        ),
        "test/evaluate": (
            {"kind": "KIND", "artifact": "ARTIFACT"},
            {"persona": "PERSONA", "assumption": "ASSUMPTION"},
        ),
    }
    for prompt_id, (shared, varying) in cases.items():
        _, rendered, _ = render_prompt(prompt_id, **shared, **varying)
        prefix, suffix = split_cache_marker(rendered)
        assert suffix, f"{prompt_id} declares no cache split"
        for value in shared.values():
            assert value in prefix and value not in suffix, f"{prompt_id}: {value} not shared"
        for value in varying.values():
            assert value in suffix and value not in prefix, f"{prompt_id}: {value} not varying"
        # The marker is framing only: the wire text still reads in template order.
        assert prefix + suffix == rendered.replace(CACHE_SPLIT, "\n")


def test_reordered_persona_prompts_keep_their_instructions() -> None:
    """A reorder must not quietly drop the framing these prompts carry."""
    from bokken.models.prompts import render_prompt

    _, turn, _ = render_prompt("empathize/persona_turn", persona="p", context="c", question="q")
    assert "in character" in turn  # stays in persona
    assert "cite its line span" in turn and "with citations" in turn  # cites spans
    assert "abstain" in turn and "real users" in turn  # abstains honestly
    assert "must be marked as such" in turn  # preferences labelled, never laundered

    _, scores, _ = render_prompt("empathize/outcome_scores", persona="p", outcomes="o")
    assert "Score EVERY outcome" in scores and "Stay in character" in scores
    assert scores.index("Desired outcomes") < scores.index("The persona you are")

    _, evaluation, _ = render_prompt(
        "test/evaluate", persona="p", kind="k", artifact="a", assumption="s"
    )
    assert "in character" in evaluation
    assert "quote the" in evaluation and "support or contradict" in evaluation
