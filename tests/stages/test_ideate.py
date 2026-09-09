"""Ideate hardening: founder pick validation, vote resolution, novelty floor."""

from pathlib import Path

import pytest

from bokken.journal import GENESIS_HASH, new_event, read_events, replay
from bokken.orchestrator import Answer, create_session
from bokken.stages.base import FOUNDER
from bokken.stages.ideate import IdeateEngine, novelty_floor
from tests.journal.conftest import AGENT
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_runner


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def test_novelty_floor_zero_is_honored() -> None:
    assert novelty_floor({"novelty_floor": 0}, {}) == 0
    assert novelty_floor({}, {"novelty_floor": 0}) == 0
    assert novelty_floor({}, {"novelty_floor": None}) == 0.2
    assert novelty_floor({}, {}) == 0.2
    assert novelty_floor({"novelty_floor": 0.5}, {"novelty_floor": 0.1}) == 0.5


def _option(seq: int, prev_hash: str, summary: str):
    return new_event(
        seq=seq,
        session_id="s1",
        type="option.created",
        stage="ideate",
        actor=AGENT,
        payload={"summary": summary},
        prev_hash=prev_hash,
    )


def test_feasibility_code_context_is_capped(tmp_path: Path) -> None:
    """The corpus rides uncached in the feasibility lens: it must stay bounded."""
    from types import SimpleNamespace

    from bokken.stages.exploration import CODE_CONTEXT_CAP_CHARS

    repo = tmp_path / "app"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "big.py").write_text("x = 1  # padding line\n" * 8000)
    ctx = SimpleNamespace(state=SimpleNamespace(config={}, brief={"inputs": {"repo": str(repo)}}))
    text = IdeateEngine._code_context(ctx)
    assert "[source " in text
    assert len(text) <= CODE_CONTEXT_CAP_CHARS


def test_votes_by_list_position_resolve_to_presented_options() -> None:
    first = _option(1, GENESIS_HASH, "option a")
    second = _option(2, first.hash, "option b")
    options = [first, second]
    assert IdeateEngine._resolve_option_id(first.id, options) == first.id
    assert IdeateEngine._resolve_option_id("1", options) == first.id
    assert IdeateEngine._resolve_option_id("2", options) == second.id
    # out of range or unknown ids are left as-is: the winner check catches them
    assert IdeateEngine._resolve_option_id("3", options) == "3"
    assert IdeateEngine._resolve_option_id("bogus", options) == "bogus"


class ScriptedFounderPort:
    def __init__(self, script: list[str]) -> None:
        self.script = list(script)

    def ask(self, question: str, *, kind: str = "text") -> Answer:
        return Answer(text=self.script.pop(0), actor=FOUNDER)


def _founder_run(name: str, pick_answers: list[str]):
    session_dir = create_session(name, brief=BRIEF, mode="founder")
    port = ScriptedFounderPort(
        [
            "arrivals were unpredictable so I quit",  # empathize answer
            "",  # ideate: no extra founder option
            *pick_answers,  # ideate: option pick (re-asked on invalid input)
            "supported: the copy speaks to the pain",  # test: assumption 1
            "contradicted: nobody tolerates detours",  # test: assumption 2
        ]
    )
    assert make_runner(session_dir, ScriptedProvider(), input_port=port).run().halt == "completed"
    state = replay(read_events(session_dir))
    return next(
        d for d in state.decisions.values() if d.question == "which concept advances to prototype"
    )


def test_founder_pick_reasks_on_invalid_input() -> None:
    decision = _founder_run("pick-reask", ["9", "not-a-number", "2"])
    assert decision.resolution == "facilitator option 2"


def test_founder_pick_falls_back_explicitly_after_three_invalid_answers() -> None:
    from bokken.journal import resolve_session_dir

    decision = _founder_run("pick-fallback", ["0", "x", "99"])
    assert decision.resolution == "facilitator option 1"
    # Nobody made a valid pick, so the default is not human testimony.
    assert decision.requires_real_validation is True
    events = list(read_events(resolve_session_dir("pick-fallback")))
    concept = next(
        e
        for e in events
        if e.type == "decision.recorded"
        and e.payload["question"] == "which concept advances to prototype"
    )
    assert concept.actor.kind != "human"  # the harness owns the default
    assert any("defaulted to option 1" in p["position"] for p in concept.payload["positions"])
