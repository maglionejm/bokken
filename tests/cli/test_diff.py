"""CLI `bokken diff`: exit-code discipline and machine-consumption output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bokken.cli.app import app
from bokken.journal import Actor, JournalStore
from bokken.orchestrator import create_session
from tests.stages.test_engines_e2e import BRIEF, make_inputs

runner = CliRunner()

FACILITATOR = Actor(kind="agent", name="facilitator")
EXPLORER = Actor(kind="agent", name="code-explorer")
PERSONA = Actor(kind="agent", name="Marta", persona_id="p-1")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def _session(name: str, *, brief: dict, populate, finalize: bool = True) -> None:
    session_dir = create_session(
        name, brief=brief, mode="dojo", gate_policy="none", config_extra={"panel": {"size": 6}}
    )
    with JournalStore.open(session_dir) as store:
        populate(store)
        if finalize:
            store.append(
                type="transition.fired",
                stage="test",
                actor=FACILITATOR,
                payload={"from_stage": "test", "to_stage": "complete", "condition": "done"},
            )


def _opportunity(store, statement, score, band):
    ev = store.append(
        type="evidence.captured",
        stage="empathize",
        actor=PERSONA,
        payload={
            "content": f"backing {statement}",
            "source": "panel interview",
            "confidence_class": "simulated",
            "speaker": "Marta",
        },
    )
    store.append(
        type="interpretation.derived",
        stage="empathize",
        actor=FACILITATOR,
        payload={"kind": "opportunity", "statement": statement, "score": score, "band": band},
        refs=[ev.id],
    )


def _capability(store, statement):
    ev = store.append(
        type="evidence.captured",
        stage="empathize",
        actor=EXPLORER,
        payload={
            "content": f"code shows {statement}",
            "source": "code exploration",
            "confidence_class": "reported",
        },
    )
    store.append(
        type="interpretation.derived",
        stage="empathize",
        actor=EXPLORER,
        payload={"kind": "current_capability", "statement": statement},
        refs=[ev.id],
    )


def _assumption(store, statement, score):
    reg = store.append(
        type="assumption.registered",
        stage="prototype",
        actor=FACILITATOR,
        payload={"statement": statement, "impact": "high", "uncertainty": "high"},
    )
    store.append(
        type="assumption.scored",
        stage="test",
        actor=FACILITATOR,
        payload={"score": score},
        refs=[reg.id],
    )


def _verdict(store, resolution):
    store.append(
        type="decision.recorded",
        stage="test",
        actor=FACILITATOR,
        payload={
            "question": "kill, iterate, or proceed",
            "options": ["kill", "iterate", "proceed"],
            "criteria": ["assumption register scores"],
            "positions": [],
            "resolution": resolution,
            "dissent": [],
        },
    )


def _seed_pair(brief: dict) -> None:
    def old(store):
        _opportunity(store, "O0: know arrival time", 12.0, "underserved")
        _assumption(store, "riders will pre-book", "untested")
        _capability(store, "record a note")
        _verdict(store, "iterate")

    def new(store):
        _opportunity(store, "O0: know arrival time", 16.0, "severely underserved")
        _assumption(store, "riders will pre-book", "supported")
        _capability(store, "record a note")
        _capability(store, "export a CSV")
        _verdict(store, "proceed")

    _session("retention-v1", brief=brief, populate=old)
    _session("retention-v2", brief=brief, populate=new)


def test_json_is_single_doc_empty_stderr_exit_zero(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    _seed_pair(brief)
    result = runner.invoke(app, ["diff", "retention-v1", "retention-v2", "--json"])
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    document = json.loads(result.stdout)  # exactly one JSON document
    assert document["kind"] == "diff"

    ops = {(o["run"], o["statement"]): o for o in document["opportunities"]}
    reranked = ops[("both", "O0: know arrival time")]
    assert reranked["old_score"] == 12.0 and reranked["new_score"] == 16.0
    assert reranked["score_delta"] == 4.0
    assert reranked["confidence_class"] == "simulated"

    flips = {a["statement"]: a for a in document["assumptions"]}
    assert flips["riders will pre-book"]["old_score"] == "untested"
    assert flips["riders will pre-book"]["new_score"] == "supported"

    caps = {c["statement"]: c for c in document["capabilities"]}
    assert caps["export a CSV"]["change"] == "added" and caps["export a CSV"]["run"] == "new"

    assert document["verdict"]["old_verdict"] == "iterate"
    assert document["verdict"]["new_verdict"] == "proceed"
    assert document["verdict"]["changed"] is True
    # every row carries run provenance and a confidence class
    for row in (*document["opportunities"], *document["assumptions"], *document["capabilities"]):
        assert row["run"] in ("both", "new", "old") and row["confidence_class"]


def test_table_contains_all_four_sections(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    _seed_pair(brief)
    result = runner.invoke(app, ["diff", "retention-v1", "retention-v2"])
    assert result.exit_code == 0, result.output
    for section in ("opportunities:", "assumptions:", "capabilities:", "verdict:"):
        assert section in result.stdout
    assert "iterate" in result.stdout and "proceed" in result.stdout
    assert "[both]" in result.stdout  # rows labelled by run of origin


def test_product_mismatch_exits_2_empty_stdout() -> None:
    _session(
        "app-alpha",
        brief={**BRIEF, "problem_space": "shuttle retention"},
        populate=lambda s: _verdict(s, "iterate"),
    )
    _session(
        "app-beta",
        brief={**BRIEF, "problem_space": "grocery delivery"},
        populate=lambda s: _verdict(s, "iterate"),
    )
    result = runner.invoke(app, ["diff", "app-alpha", "app-beta"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "not the same product" in result.stderr


def test_unfinalized_exits_2_empty_stdout(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    _session("done-run", brief=brief, populate=lambda s: _verdict(s, "iterate"))
    _session("in-flight-run", brief=brief, populate=lambda s: None, finalize=False)
    result = runner.invoke(app, ["diff", "done-run", "in-flight-run"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "in-flight-run" in result.stderr and "not finalized" in result.stderr


def test_unknown_session_exits_2() -> None:
    result = runner.invoke(app, ["diff", "ghost-a", "ghost-b"])
    assert result.exit_code == 2
    assert result.stdout == ""
