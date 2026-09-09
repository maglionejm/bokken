"""Code exploration: cited current-capability findings before anyone is interviewed."""

from __future__ import annotations

from bokken.journal.store import JournalStore
from bokken.models import ModelRouter
from bokken.models.router import ModelOutcome
from bokken.panel.corpus import Citation, Corpus
from bokken.stages import schemas as s
from bokken.stages.exploration import CODE_CONTEXT_CAP_CHARS, run_code_exploration
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import make_inputs


def test_capabilities_are_journaled_with_valid_citations(tmp_path):
    corpus = Corpus.ingest_inputs(make_inputs(tmp_path))
    with JournalStore.open(tmp_path / "s") as store:
        router = ModelRouter(store, ScriptedProvider())
        text = run_code_exploration(corpus, store, router)
        events = list(store.events())
    caps = [e for e in events if e.type == "interpretation.derived"]
    assert len(caps) == 2
    for e in caps:
        assert e.payload["kind"] == "current_capability"
        assert e.payload["ungrounded"] is False
        for c in e.payload["citations"]:
            assert c["source_id"] in corpus.source_ids
    assert "record a note" in text


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
