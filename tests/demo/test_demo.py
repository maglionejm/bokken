"""Acceptance tests for `bokken demo` (issue #27): offline, cited, deterministic."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from bokken.demo import FIXTURES, run_demo

ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}T[0-9:.+Z-]+")
HEX = re.compile(r"\b[0-9a-f]{12,64}\b")


@pytest.fixture(scope="module")
def demo_runs(tmp_path_factory, monkeypatch_module=None):
    home = tmp_path_factory.mktemp("bokken-home")
    mp = pytest.MonkeyPatch()
    mp.setenv("BOKKEN_HOME", str(home))
    mp.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        yield run_demo("demo-a"), run_demo("demo-b")
    finally:
        mp.undo()


def _events(session_dir: Path) -> list[dict]:
    lines = (session_dir / "journal.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def test_demo_runs_offline_to_a_full_report(demo_runs):
    first, _ = demo_runs
    assert first["report_html"].exists()
    assert first["report_pptx"].exists()
    assert first["dossier"].exists()
    html = first["report_html"].read_text()
    assert "Ventana honesta" in html
    assert "Simulated run" in html or "simulated" in html.lower()


def test_demo_costs_zero_tokens(demo_runs):
    first, _ = demo_runs
    for event in _events(first["session_dir"]):
        usage = event.get("payload", {}).get("usage")
        if usage:
            assert usage.get("input_tokens", 0) == 0
            assert usage.get("output_tokens", 0) == 0


def test_demo_citations_resolve_against_bundled_corpus(demo_runs):
    from bokken.demo import DEMO_BRIEF
    from bokken.panel.corpus import Corpus

    first, _ = demo_runs
    corpus = Corpus.ingest_inputs(DEMO_BRIEF["inputs"])
    raw = corpus._sources
    srcs = raw if isinstance(raw, list) else list(raw.values())
    lines_by_id = {src.source_id: len(src.lines) for src in srcs}
    cited = [
        c
        for e in _events(first["session_dir"])
        if e["type"] == "evidence.captured"
        for c in e["payload"].get("citations", [])
    ]
    assert cited, "demo produced no grounded citations"
    for c in cited:
        assert c["source_id"] in lines_by_id
        assert 1 <= c["start_line"] <= c["end_line"] <= lines_by_id[c["source_id"]]


def test_demo_tells_the_engineered_story(demo_runs):
    first, _ = demo_runs
    md = first["dossier"].read_text()
    assert "iterate" in md.lower()
    assert "16" in md  # the underserved winner's Ulwick opportunity score
    dissents = [
        d
        for e in _events(first["session_dir"])
        if e["type"] == "decision.recorded"
        for d in e["payload"].get("dissent", [])
    ]
    assert any("red verdict" in d.get("reservation", "") for d in dissents)


def test_demo_is_deterministic_apart_from_name_and_time(demo_runs):
    first, second = demo_runs

    def normalize(run):
        text = run["dossier"].read_text()
        text = text.replace(run["session_dir"].name, "SESSION")
        text = ISO_TS.sub("TS", text)
        return HEX.sub("ID", text)

    assert normalize(first) == normalize(second)


def test_fixtures_ship_with_the_package():
    assert (FIXTURES / "repo" / "README.md").exists()
    assert (FIXTURES / "kpis.csv").exists()
    for name in ("interview_marta.md", "interview_diego.md"):
        assert (FIXTURES / name).exists()
