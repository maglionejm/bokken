"""Code exploration: cited current-capability findings before anyone is interviewed."""

from __future__ import annotations

import pytest

from bokken.journal.schema import Actor
from bokken.journal.store import JournalStore
from bokken.models import ModelRouter
from bokken.models.router import ModelOutcome
from bokken.orchestrator import Answer, InputRequired
from bokken.orchestrator.runner import NoInputPort
from bokken.panel.corpus import Citation, Corpus
from bokken.stages import schemas as s
from bokken.stages.exploration import CODE_CONTEXT_CAP_CHARS, run_code_exploration
from tests.stages.fake_provider import SOURCE, ScriptedProvider
from tests.stages.test_engines_e2e import make_inputs


def test_capabilities_are_journaled_with_valid_citations(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        text = run_code_exploration(corpus, store, router)
        events = list(store.events())
    caps = [e for e in events if e.payload.get("kind") == "current_capability"]
    assert len(caps) == 2
    for e in caps:
        assert e.payload["ungrounded"] is False
        for c in e.payload["citations"]:
            assert c["source_id"] in corpus.source_ids
    assert "record a note" in text


def test_citations_carry_truncated_verbatim_quotes(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        run_code_exploration(corpus, store, router)
        events = list(store.events())
    caps = [e for e in events if e.payload.get("kind") == "current_capability"]
    assert caps
    for e in caps:
        for c in e.payload["citations"]:
            span = corpus.span(Citation.model_validate({k: c[k] for k in Citation.model_fields}))
            assert c["quote"]
            assert len(c["quote"]) <= 200
            assert span.startswith(c["quote"]) or c["quote"].rstrip(".") in span


class LongSpanProvider(ScriptedProvider):
    """Cites a span far larger than the quote cap, as a generous model would."""

    def _dispatch(self, prompt_id, rendered):
        if prompt_id == "explore/capability_map":
            sources = SOURCE.findall(rendered)
            return s.CapabilityMap(
                capabilities=[
                    s.CurrentCapability(
                        name="long behavior",
                        actor="the app",
                        trigger="always",
                        outcome="a lot of code runs",
                        citations=[Citation(source_id=sources[0], start_line=1, end_line=40)],
                    )
                ]
            )
        return super()._dispatch(prompt_id, rendered)


def test_quotes_are_deterministically_truncated_to_200_chars(tmp_path):
    repo = tmp_path / "app"
    repo.mkdir()
    (repo / "main.py").write_text("def handler():  # a deliberately verbose line of code\n" * 40)
    corpus = Corpus.ingest_inputs({"repo": str(repo)})
    with JournalStore.open(tmp_path / "s") as store:
        run_code_exploration(corpus, store, ModelRouter(store, LongSpanProvider()))
        caps = [e for e in store.events() if e.payload.get("kind") == "current_capability"]
    quote = caps[0].payload["citations"][0]["quote"]
    assert len(quote) == 200
    assert quote.endswith("...")
    assert quote.startswith("def handler():")


def test_no_code_sources_is_a_quiet_noop(tmp_path):
    metrics = tmp_path / "kpis.csv"
    metrics.write_text("month,value\n1,2\n")
    corpus = Corpus.ingest_inputs({"metrics": [str(metrics)]})
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        assert run_code_exploration(corpus, store, router) == ""
        assert not [e for e in store.events() if e.type == "model.called"]


def test_context_headers_carry_evidence_roles(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    ctx = corpus.context_for()
    assert "establishes implemented behavior, not desired intent" in ctx


class ExhaustedRouter:
    """Every invocation reports its budget spent, as the real router would."""

    def invoke(self, *args, **kwargs):
        return ModelOutcome(status="budget_exhausted", detail="total budget spent")


def test_budget_exhaustion_is_none_not_an_empty_map(tmp_path):
    """None (stop the run) must stay distinguishable from '' (no code sources)."""
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        assert run_code_exploration(corpus, store, ExhaustedRouter()) is None
        assert not [e for e in store.events() if e.type == "interpretation.derived"]


class CrossKindProvider(ScriptedProvider):
    """Cites a resolvable span in a non-code source, as a sloppy model would."""

    def __init__(self, cite_id: str) -> None:
        super().__init__()
        self.cite_id = cite_id

    def _dispatch(self, prompt_id, rendered):
        if prompt_id == "explore/capability_map":
            return s.CapabilityMap(
                capabilities=[
                    s.CurrentCapability(
                        name="churn is tracked",
                        actor="the team",
                        trigger="monthly",
                        outcome="a churn figure exists",
                        citations=[Citation(source_id=self.cite_id, start_line=1, end_line=1)],
                    )
                ]
            )
        return super()._dispatch(prompt_id, rendered)


def test_citations_into_non_code_sources_do_not_ground_a_capability(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    metrics_id = corpus.ids_of_kind("metrics")[0]
    assert corpus.validate_citation(Citation(source_id=metrics_id, start_line=1, end_line=1))
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, CrossKindProvider(metrics_id))
        text = run_code_exploration(corpus, store, router)
        caps = [e for e in store.events() if e.type == "interpretation.derived"]
    assert len(caps) == 1
    assert caps[0].payload["ungrounded"] is True
    assert caps[0].payload["citations"] == []
    assert "(ungrounded)" in text


def test_glossary_terms_are_journaled_with_quoted_citations(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        run_code_exploration(corpus, store, ModelRouter(store, ScriptedProvider()))
        terms = [e for e in store.events() if e.payload.get("kind") == "domain_term"]
    assert terms, "the capability-map call journals no domain_term interpretations"
    for e in terms:
        assert e.payload["ungrounded"] is False
        assert e.payload["citations"]
        for c in e.payload["citations"]:
            assert c["source_id"] in corpus.source_ids
            assert c["quote"] and len(c["quote"]) <= 200


class RatifyPort:
    """A founder at the terminal answering ratification prompts from a script."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.questions: list[str] = []

    def ask(self, question: str, *, kind: str = "text") -> Answer:
        self.questions.append(question)
        return Answer(text=self.answers.pop(0), actor=Actor(kind="human", name="founder"))


def _explore_with_port(tmp_path, answers):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    port = RatifyPort(answers)
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        run_code_exploration(corpus, store, router, input_port=port)
        events = list(store.events())
    caps = [e for e in events if e.payload.get("kind") == "current_capability"]
    human = [e for e in events if e.type == "evidence.captured" and e.actor.kind == "human"]
    return caps, human, port


def test_founder_confirmation_marks_the_interpretation_ratified(tmp_path):
    caps, human, port = _explore_with_port(tmp_path, ["c", "d notes are lost, never counted"])
    assert len(caps) == 2
    assert caps[0].payload["ratified"] is True
    assert caps[1].payload["ratified"] is False
    assert len(port.questions) == 2  # one compact prompt per capability
    (dispute,) = human
    assert dispute.payload["content"] == "notes are lost, never counted"
    assert dispute.payload["confidence_class"] == "reported"
    assert dispute.refs == [caps[1].id]


def test_bare_dispute_asks_once_for_the_correction(tmp_path):
    caps, human, port = _explore_with_port(tmp_path, ["d", "sync failures are silent", "s"])
    assert len(port.questions) == 3  # capability prompt, correction ask, capability prompt
    assert caps[0].payload["ratified"] is False
    (dispute,) = human
    assert dispute.payload["content"] == "sync failures are silent"
    assert dispute.refs == [caps[0].id]
    assert "ratified" not in caps[1].payload


def test_skips_and_unrecognized_answers_journal_nothing(tmp_path):
    caps, human, _ = _explore_with_port(tmp_path, ["s", "whatever comes to mind"])
    assert all("ratified" not in e.payload for e in caps)
    assert not human


def test_dojo_runs_never_ratify(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        run_code_exploration(corpus, store, ModelRouter(store, ScriptedProvider()))
        caps = [e for e in store.events() if e.payload.get("kind") == "current_capability"]
    assert caps
    assert all("ratified" not in e.payload for e in caps)


def test_headless_ratification_propagates_input_required(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        with pytest.raises(InputRequired):
            run_code_exploration(corpus, store, router, input_port=NoInputPort())


class RenderedCapture(ScriptedProvider):
    last_rendered = ""

    def complete(self, **kwargs):
        self.last_rendered = kwargs["rendered"]
        return super().complete(**kwargs)


def test_exploration_context_is_capped(tmp_path):
    repo = tmp_path / "app"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "big.py").write_text("x = 1  # padding line\n" * 8000)
    corpus = Corpus.ingest_inputs({"repo": str(repo)})
    assert len(corpus.context_for(corpus.ids_of_kind("code"))) > CODE_CONTEXT_CAP_CHARS
    provider = RenderedCapture()
    with JournalStore.open(tmp_path / "s") as store:
        run_code_exploration(corpus, store, ModelRouter(store, provider))
    # cap plus the template's own instruction text, never the full corpus
    assert len(provider.last_rendered) < CODE_CONTEXT_CAP_CHARS + 2000
