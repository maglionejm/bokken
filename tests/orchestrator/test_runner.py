from pathlib import Path

import pytest

from bokken.journal import Actor, read_events, replay
from bokken.orchestrator import (
    Answer,
    IllegalTransitionError,
    MissingEngineError,
    Runner,
    SelfEscalationError,
    StageContext,
    StageOutcome,
    StalledStageError,
    create_session,
)
from tests.journal.conftest import BRIEF
from tests.orchestrator.fakes import (
    AskingEmpathizeFake,
    BurnBudgetFake,
    NoopFake,
    full_engine_suite,
)

HUMAN = Actor(kind="human", name="founder")
AGENT = Actor(kind="agent", name="rogue", model="fake")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path))
    return tmp_path


class ScriptedPort:
    """Stands in for the terminal: answers come from a real human."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = answers

    def ask(self, question: str, *, kind: str = "text") -> Answer:
        return Answer(text=self.answers.pop(0), actor=HUMAN)


def founder_session(name: str = "s1", **kw):
    return create_session(name, brief=BRIEF, mode="founder", **kw)


def test_founder_run_to_completion_without_gates() -> None:
    session_dir = founder_session()
    result = Runner(session_dir, engines=full_engine_suite()).run()
    assert result.halt == "completed"
    state = replay(read_events(session_dir))
    assert state.stage == "complete"
    hops = [(t["from"], t["to"]) for t in state.transitions]
    assert hops == [
        ("intake", "empathize"),
        ("empathize", "define"),
        ("define", "ideate"),
        ("ideate", "prototype"),
        ("prototype", "test"),
        ("test", "complete"),
    ]


def test_transitions_carry_conditions_and_justification_refs() -> None:
    session_dir = founder_session()
    Runner(session_dir, engines=full_engine_suite()).run()
    state = replay(read_events(session_dir))
    assert {t["condition"] for t in state.transitions} == {"exit criteria met"}
    define_to_ideate = next(t for t in state.transitions if t["from"] == "define")
    define_decision = next(d for d in state.decisions.values() if d.stage == "define")
    assert define_decision.id in define_to_ideate["refs"]


def test_step_advances_at_most_one_stage() -> None:
    session_dir = founder_session()
    runner = Runner(session_dir, engines=full_engine_suite())
    result = runner.step()
    assert result.halt == "stepped"
    assert replay(read_events(session_dir)).stage == "empathize"


def test_dojo_run_halts_at_every_gate_and_rejection_keeps_stage() -> None:
    session_dir = create_session("dojo-1", brief=BRIEF, mode="dojo")
    runner = Runner(session_dir, engines=full_engine_suite())

    result = runner.run()
    assert result.halt == "gate_pending"
    state = replay(read_events(session_dir))
    assert state.pending_gate is not None
    assert state.pending_gate.from_stage == "intake"

    runner.resolve_gate(resolution="reject", actor=HUMAN, reason="brief too vague")
    state = replay(read_events(session_dir))
    assert state.stage == "intake" and state.pending_gate is None

    gates = 0
    while True:
        result = runner.run()
        if result.halt == "completed":
            break
        assert result.halt == "gate_pending"
        gates += 1
        runner.resolve_gate(resolution="approve", actor=HUMAN)
    assert gates == 6
    assert replay(read_events(session_dir)).stage == "complete"


def test_gate_resolution_works_across_processes() -> None:
    session_dir = create_session("dojo-2", brief=BRIEF, mode="dojo")
    Runner(session_dir, engines=full_engine_suite()).run()
    # A second, independent runner (fresh handle, as the CLI would be) resolves.
    Runner(session_dir).resolve_gate(resolution="approve", actor=HUMAN)
    state = replay(read_events(session_dir))
    assert state.pending_gate is None and state.approved_gate is not None


def test_input_pending_halt_and_scripted_resume() -> None:
    session_dir = founder_session()
    engines = full_engine_suite() | {"empathize": AskingEmpathizeFake()}
    result = Runner(session_dir, engines=engines).run()
    assert result.halt == "input_pending"
    assert "last time" in (result.pending_question or "")

    port = ScriptedPort(["it hit me on Tuesday's commute"])
    result = Runner(session_dir, engines=engines, input_port=port).run()
    assert result.halt == "completed"
    events = list(read_events(session_dir))
    assert any(e.type == "session.resumed" for e in events)


def test_budget_exhaustion_stops_and_human_raise_resumes() -> None:
    session_dir = create_session(
        "budget-1", brief=BRIEF, mode="founder", budgets={"total_tokens": 1000}
    )
    engines = full_engine_suite() | {"empathize": BurnBudgetFake()}
    result = Runner(session_dir, engines=engines).run()
    assert result.halt == "stopped" and result.detail == "budget_exhausted"
    stopped = [e for e in read_events(session_dir) if e.type == "session.stopped"]
    assert len(stopped) == 1 and stopped[0].payload["reason"] == "budget_exhausted"

    result = Runner(session_dir, engines=full_engine_suite()).run(
        config_overrides={"budgets": {"total_tokens": 50_000}}, actor=HUMAN
    )
    assert result.halt == "completed"


class CachedBurnBudgetFake:
    """Empathize engine whose spend is almost entirely a cached prompt prefix."""

    def run(self, ctx: StageContext) -> StageOutcome | None:
        ctx.store.append(
            type="model.called",
            stage="empathize",
            actor=Actor(kind="agent", name="facilitator", model="claude-fable-5"),
            payload={
                "routing_class": "research",
                "model": "claude-fable-5",
                "prompt_id": "empathize/interview",
                "prompt_version": "v1",
                "prompt_hash": "h",
                "usage": {
                    "input_tokens": 5_000,
                    "output_tokens": 500,
                    "cache_read_tokens": 195_000,
                    "cache_write_tokens": 0,
                },
                "status": "ok",
            },
        )
        return None


def test_budget_stops_run_when_spend_is_mostly_cache_reads() -> None:
    """The budget is a governance control, so a cached prompt cannot defer it:
    one 200,500-token call blows a 100,000-token budget even though only 5,500
    of those tokens are uncached input plus output."""
    session_dir = create_session(
        "budget-cached", brief=BRIEF, mode="founder", budgets={"total_tokens": 100_000}
    )
    engines = full_engine_suite() | {"empathize": CachedBurnBudgetFake()}
    result = Runner(session_dir, engines=engines).run()
    assert result.halt == "stopped" and result.detail == "budget_exhausted"
    stopped = [e for e in read_events(session_dir) if e.type == "session.stopped"]
    assert len(stopped) == 1 and stopped[0].payload["reason"] == "budget_exhausted"
    state = replay(read_events(session_dir))
    assert state.tokens_spent() == 200_500


def test_agent_cannot_override_config() -> None:
    session_dir = founder_session()
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()
    with pytest.raises(SelfEscalationError):
        runner.run(config_overrides={"budgets": {"total_tokens": 10**9}}, actor=AGENT)
    suppressed = [e for e in read_events(session_dir) if e.type == "facilitation.move_suppressed"]
    assert suppressed and suppressed[-1].payload["move_id"] == "config_change_attempt"


def test_brief_and_gate_policy_are_immutable_even_for_humans() -> None:
    session_dir = founder_session()
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()
    for key in ("brief", "gate_policy"):
        with pytest.raises(SelfEscalationError):
            runner.run(config_overrides={key: {}}, actor=HUMAN)


def test_human_loopback_legal_and_illegal() -> None:
    session_dir = founder_session()
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()  # -> empathize
    runner.step()  # -> define
    with pytest.raises(IllegalTransitionError, match="legal targets"):
        runner.request_loopback(to_stage="prototype", reason="nope", actor=HUMAN)
    runner.request_loopback(to_stage="empathize", reason="segment unheard", actor=HUMAN)
    state = replay(read_events(session_dir))
    assert state.stage == "empathize"
    assert "human loop-back" in state.transitions[-1]["condition"]


def test_loopback_forces_engine_rework_before_fast_forward() -> None:
    session_dir = founder_session()
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()  # -> empathize
    runner.step()  # -> define (empathize criteria now satisfied)
    evidence_before = len(replay(read_events(session_dir)).evidence)
    runner.request_loopback(to_stage="empathize", reason="segment unheard", actor=HUMAN)
    # Without rework, empathize criteria are already met and the run would fast-forward.
    result = Runner(session_dir, engines=full_engine_suite()).run()
    assert result.halt == "completed"
    state = replay(read_events(session_dir))
    assert len(state.evidence) > evidence_before  # the engine actually ran again
    reworked = [t for t in state.transitions if t["from"] == "empathize"]
    assert len(reworked) == 2  # original pass + post-loop-back rework


def test_stop_is_journaled_human_stop() -> None:
    session_dir = founder_session()
    Runner(session_dir).stop(actor=HUMAN, detail="lunch")
    state = replay(read_events(session_dir))
    assert state.stopped == "human_stop"


def test_missing_engine_and_stalled_engine_raise() -> None:
    session_dir = founder_session()
    with pytest.raises(MissingEngineError):
        Runner(session_dir, engines={}).run()
    session_dir2 = create_session("s2", brief=BRIEF, mode="founder")
    with pytest.raises(StalledStageError):
        Runner(session_dir2, engines={"empathize": NoopFake()}).run()


def test_mode_parity_same_event_families() -> None:
    founder_dir = create_session("parity-f", brief=BRIEF, mode="founder")
    dojo_dir = create_session("parity-d", brief=BRIEF, mode="dojo", gate_policy="none")
    Runner(founder_dir, engines=full_engine_suite()).run()
    Runner(dojo_dir, engines=full_engine_suite()).run()

    def families(session_dir):
        return {e.type.split(".")[0] for e in read_events(session_dir)}

    assert families(founder_dir) == families(dojo_dir)
    founder_state = replay(read_events(founder_dir))
    dojo_state = replay(read_events(dojo_dir))
    assert founder_state.evidence_by_class == {"observed": 1}
    assert dojo_state.evidence_by_class == {"simulated": 1}
