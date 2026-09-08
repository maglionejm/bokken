"""Code exploration: cited current-capability findings before anyone is interviewed."""

from __future__ import annotations

from bokken.journal.store import JournalStore
from bokken.models import ModelRouter
from bokken.panel.corpus import Corpus
from bokken.stages.exploration import run_code_exploration
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
