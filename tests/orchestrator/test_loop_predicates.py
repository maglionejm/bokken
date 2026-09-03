"""The run loop's correctness predicates, tested one at a time.

Two of these predicates used to fail open. An unrecognized gate policy fell
through to a membership test and produced a run with zero gates; the rework
requirement after a loop-back was discharged by any appended record at all,
including the engine's own refused model call. Both classes of failure are
governance failures, so each has a test here that fails on the old behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bokken.journal import Actor, JournalStore, create_session_dir, read_events, replay
from bokken.journal.replay import PendingGate
from bokken.orchestrator import Runner, StalledStageError, create_session
from bokken.orchestrator.machine import FORWARD
from bokken.orchestrator.runner import (
    SYSTEM_ACTOR,
    GatePolicyError,
    StageContext,
    StageOutcome,
    approved_gate_target,
    default_gate_policy,
    gate_required,
    halt_result,
    is_substantive_work,
    normalize_gate_policy,
    resolve_gate_policy,
    rework_pending,
)
from tests.journal.conftest import BRIEF
from tests.orchestrator.fakes import full_engine_suite

HUMAN = Actor(kind="human", name="founder")
AGENT = Actor(kind="agent", name="facilitator", model="fake")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path))
    return tmp_path


def _journal_with_config(name: str, config: dict, mode: str = "dojo") -> Path:
    """A session whose journaled config was not written by ``create_session`` —
    an older Bokken, or a hand-edited config file."""
    session_dir = create_session_dir(name)
    with JournalStore.open(session_dir) as store:
        store.append(
            type="session.created",
            stage="intake",
            actor=SYSTEM_ACTOR,
            payload={"name": name, "mode": mode, "brief": BRIEF, "config": config},
        )
    return session_dir


# -- gate policy -----------------------------------------------------------


def test_recognized_gate_policies_normalize_to_themselves() -> None:
    assert normalize_gate_policy("none") == "none"
    assert normalize_gate_policy("stage_boundaries") == "stage_boundaries"
    assert normalize_gate_policy(["define", "test"]) == ["define", "test"]
    assert normalize_gate_policy([]) == []


@pytest.mark.parametrize(
    "policy",
    [
        "stage_boundary",  # the singular typo that used to disable every gate
        "stage-boundaries",
        "all",
        "define,test",  # a comma-joined string, never split by the runner
        "",
        ["define", "stage_boundary"],
        ["stage_boundary"],
        ["complete"],  # terminal stage: a gate there could never fire
        [""],
        {"define": True},
        7,
        None,
        True,
    ],
)
def test_unrecognized_gate_policy_is_refused_loudly(policy: object) -> None:
    with pytest.raises(GatePolicyError):
        normalize_gate_policy(policy)


def test_gate_policy_refusal_names_the_legal_forms() -> None:
    with pytest.raises(GatePolicyError, match="stage_boundaries"):
        normalize_gate_policy("stage_boundary")


def test_gate_required_only_ever_tests_membership_of_real_stages() -> None:
    assert not gate_required("none", "define")
    assert all(gate_required("stage_boundaries", stage) for stage in FORWARD)
    policy = normalize_gate_policy(["define"])
    assert gate_required(policy, "define")
    assert not gate_required(policy, "empathize")


def test_undeclared_policy_resolves_from_the_mode_never_to_no_gates() -> None:
    assert default_gate_policy("founder") == "none"
    assert default_gate_policy("dojo") == "stage_boundaries"
    assert default_gate_policy(None) == "stage_boundaries"
    state = replay(read_events(_journal_with_config("undeclared", {"budgets": {}})))
    assert resolve_gate_policy(state) == "stage_boundaries"


def test_dojo_journal_that_declares_no_policy_still_gates() -> None:
    """An absent policy is "not declared", never "no gates": a dojo run whose
    config never named a policy halts for approval like any other dojo run."""
    session_dir = _journal_with_config("undeclared-run", {"budgets": {}})
    result = Runner(session_dir, engines=full_engine_suite()).run()
    assert result.halt == "gate_pending"


def test_typoed_gate_policy_is_refused_before_the_session_exists(tmp_path: Path) -> None:
    with pytest.raises(GatePolicyError, match="stage_boundary"):
        create_session("typo-new", brief=BRIEF, mode="dojo", gate_policy="stage_boundary")
    assert not (tmp_path / "sessions" / "typo-new").exists()


def test_typoed_gate_policy_in_config_extra_is_refused_too(tmp_path: Path) -> None:
    with pytest.raises(GatePolicyError):
        create_session(
            "typo-extra",
            brief=BRIEF,
            mode="dojo",
            config_extra={"gate_policy": "stage_boundary"},
        )
    assert not (tmp_path / "sessions" / "typo-extra").exists()


def test_typoed_gate_policy_never_yields_a_gateless_run() -> None:
    """The live bug: a one-item list of a bogus policy name made the membership
    test false at every stage, so the run sprinted intake -> complete requesting
    zero gates. It must refuse instead, before doing any work at all."""
    session_dir = _journal_with_config("typo-run", {"gate_policy": "stage_boundary"})
    runner = Runner(session_dir, engines=full_engine_suite())
    with pytest.raises(GatePolicyError, match="unknown gate policy"):
        runner.run()
    events = list(read_events(session_dir))
    assert [e.type for e in events] == ["session.created"]  # nothing was journaled
    assert replay(events).stage == "intake"


def test_stage_list_gate_policy_still_gates_exactly_its_stages() -> None:
    session_dir = create_session("list-policy", brief=BRIEF, mode="dojo", gate_policy=["define"])
    runner = Runner(session_dir, engines=full_engine_suite())
    result = runner.run()
    assert result.halt == "gate_pending"
    state = replay(read_events(session_dir))
    assert state.pending_gate is not None and state.pending_gate.from_stage == "define"
    runner.resolve_gate(resolution="approve", actor=HUMAN)
    assert runner.run().halt == "completed"
    gates = [e for e in read_events(session_dir) if e.type == "session.gate_requested"]
    assert [e.payload["from_stage"] for e in gates] == ["define"]


# -- rework after a loop-back ----------------------------------------------


class RefusedCallFake:
    """An engine whose model call is refused: the refusal is journaled (it is a
    real cost and a real event) and the engine reports no outcome."""

    def __init__(self, stage: str = "empathize") -> None:
        self.stage = stage
        self.runs = 0

    def run(self, ctx: StageContext) -> StageOutcome | None:
        self.runs += 1
        ctx.store.append(
            type="model.called",
            stage=self.stage,  # type: ignore[arg-type]
            actor=AGENT,
            payload={
                "routing_class": "research",
                "model": "fake",
                "prompt_id": "empathize/interview_program",
                "prompt_version": "v1",
                "prompt_hash": "h",
                "usage": {"input_tokens": 10, "output_tokens": 0},
                "status": "refused",
            },
        )
        return None


@pytest.mark.parametrize(
    ("event_type", "substantive"),
    [
        ("evidence.captured", True),
        ("evidence.abstained", True),
        ("interpretation.derived", True),
        ("option.created", True),
        ("decision.recorded", True),
        ("assumption.scored", True),
        ("artifact.generated", True),
        ("facilitation.move_executed", True),
        ("model.called", False),
        ("facilitation.move_suppressed", False),
        ("evidence.input_rejected", False),
        ("transition.fired", False),
        ("session.resumed", False),
        ("session.gate_resolved", False),
        ("nobody.classified_this", False),
    ],
)
def test_substantive_work_classification(event_type: str, substantive: bool) -> None:
    assert is_substantive_work(event_type) is substantive


def _loopback_state(session_dir: Path):
    events = list(read_events(session_dir))
    return replay(events), events


def test_rework_pending_needs_work_by_the_target_stage() -> None:
    session_dir = create_session("rework-unit", brief=BRIEF, mode="founder")
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()  # -> empathize
    runner.step()  # -> define
    state, events = _loopback_state(session_dir)
    assert not rework_pending(state, events)  # a forward transition is not rework

    runner.request_loopback(to_stage="empathize", reason="segment unheard", actor=HUMAN)
    state, events = _loopback_state(session_dir)
    assert rework_pending(state, events)

    with JournalStore.open(session_dir) as store:
        # Telemetry, a suppressed move, and work stamped with another stage all
        # leave the loop-back's rework requirement outstanding.
        store.append(
            type="model.called",
            stage="empathize",
            actor=AGENT,
            payload={
                "routing_class": "research",
                "model": "fake",
                "prompt_id": "p",
                "prompt_version": "v1",
                "prompt_hash": "h",
                "status": "refused",
            },
        )
        store.append(
            type="facilitation.move_suppressed",
            stage="empathize",
            actor=AGENT,
            payload={"move_id": "probe", "trigger": "x", "reason": "out_of_stage"},
        )
        store.append(
            type="interpretation.derived",
            stage="define",
            actor=AGENT,
            payload={"kind": "insight", "statement": "stale", "ungrounded": True},
        )
    state, events = _loopback_state(session_dir)
    assert rework_pending(state, events)

    with JournalStore.open(session_dir) as store:
        store.append(
            type="evidence.captured",
            stage="empathize",
            actor=HUMAN,
            payload={
                "content": "the segment finally spoke",
                "source": "interview",
                "confidence_class": "observed",
                "segment": "commuters",
            },
        )
    state, events = _loopback_state(session_dir)
    assert not rework_pending(state, events)


def test_loopback_with_only_a_refused_call_does_not_fast_forward() -> None:
    """The live bug: the refused call alone pushed events_since_transition past
    zero, so the loop fast-forwarded on exactly the evidence the human looped
    back to replace. The human's intervention must not become a no-op."""
    session_dir = create_session("rework-refused", brief=BRIEF, mode="founder")
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()  # -> empathize
    runner.step()  # -> define
    before = replay(read_events(session_dir))
    runner.request_loopback(to_stage="empathize", reason="segment unheard", actor=HUMAN)

    engine = RefusedCallFake()
    stalled = Runner(session_dir, engines=full_engine_suite() | {"empathize": engine})
    with pytest.raises(StalledStageError, match="loop-back"):
        stalled.run()

    state = replay(read_events(session_dir))
    assert state.stage == "empathize"  # never left the stage it was sent back to
    assert len(state.evidence) == len(before.evidence)  # no new grounding either
    hops = [(t["from"], t["to"]) for t in state.transitions]
    assert hops[-1] == ("define", "empathize")  # the loop-back is the last word
    assert engine.runs == Runner.MAX_ENGINE_ATTEMPTS_PER_STAGE


def test_loopback_rework_is_satisfied_by_real_work() -> None:
    """The counterpart: an engine that does journal substantive work clears the
    requirement, so requiring rework does not deadlock a legitimate loop-back."""
    session_dir = create_session("rework-real", brief=BRIEF, mode="founder")
    runner = Runner(session_dir, engines=full_engine_suite())
    runner.step()
    runner.step()
    runner.request_loopback(to_stage="empathize", reason="segment unheard", actor=HUMAN)
    assert Runner(session_dir, engines=full_engine_suite()).run().halt == "completed"


# -- halting and stale gates -----------------------------------------------


def test_halt_result_precedence() -> None:
    session_dir = create_session("halts", brief=BRIEF, mode="founder")
    state = replay(read_events(session_dir))
    assert halt_result(state) is None

    state.stopped = "human_stop"
    stopped = halt_result(state)
    assert stopped is not None and stopped.halt == "stopped" and stopped.detail == "human_stop"

    state.pending_gate = PendingGate("g-1", "define", "ideate", "operator")
    gated = halt_result(state)  # a pending gate outranks a stop
    assert gated is not None and gated.halt == "gate_pending"
    assert "g-1 guards define -> ideate" in gated.detail

    state.stage = "complete"
    completed = halt_result(state)  # completion outranks everything
    assert completed is not None and completed.halt == "completed"


def test_approved_gate_fires_only_for_the_stage_it_guards() -> None:
    session_dir = create_session("stale-gate", brief=BRIEF, mode="dojo")
    Runner(session_dir, engines=full_engine_suite()).run()  # halts on the intake gate
    Runner(session_dir).resolve_gate(resolution="approve", actor=HUMAN)
    state = replay(read_events(session_dir))
    assert approved_gate_target(state) == "empathize"

    state.stage = "define"  # a loop-back moved the run since the approval
    assert approved_gate_target(state) is None
