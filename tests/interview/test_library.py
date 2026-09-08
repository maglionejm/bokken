"""Cross-run library: learnings compound with provenance."""

from pathlib import Path

import pytest

from bokken.library import append_learnings, prior_learnings_text, read_learnings
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs, make_runner


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def test_learnings_compound_and_seed_the_next_run(tmp_path):
    from bokken.orchestrator import create_session

    inputs = make_inputs(tmp_path)
    brief = {**BRIEF, "inputs": inputs}
    session_dir = create_session(
        "lib-r1",
        brief=brief,
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    assert make_runner(session_dir, ScriptedProvider()).run().halt == "completed"
    record = append_learnings(session_dir)
    assert record and record["verdict"] == "iterate"
    assert any(a["score"] == "contradicted" for a in record["assumptions"])
    # idempotent
    assert append_learnings(session_dir) is None
    assert len(read_learnings()) == 1

    seeded = prior_learnings_text(brief, exclude_session="lib-r2")
    assert "lib-r1" in seeded and "[contradicted]" in seeded
    # a different product sees nothing
    assert "(no prior runs" in prior_learnings_text({"problem_space": "otro"})


def test_read_learnings_tolerates_torn_and_legacy_lines():
    import json

    from bokken.library import _library_path

    path = _library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    good = {
        "ts": "2026-01-01T00:00:00+00:00",
        "session": "s1",
        "product": "p",
        "verdict": "iterate",
        "assumptions": [{"statement": "x", "score": "supported"}],
        "opportunities": [],
        "ui_broken": [],
    }
    path.write_text(
        json.dumps(good)
        + "\n"
        + '{"session": "torn", "produ\n'  # a torn partial write
        + json.dumps({"session": "legacy"})
        + "\n"  # a legacy record missing keys
    )
    assert [r["session"] for r in read_learnings()] == ["s1", "legacy"]
    assert [r["session"] for r in read_learnings("p")] == ["s1"]
    digest = prior_learnings_text({"problem_space": "p"})
    assert "[supported] x" in digest
