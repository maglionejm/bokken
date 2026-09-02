"""Offline end-to-end runs: the full DT loop with the scripted provider."""

from pathlib import Path

import pytest

from bokken.journal import Actor, read_events, replay
from bokken.kata import MVP_MOVES, Kata
from bokken.models import ModelRouter
from bokken.orchestrator import Answer, Runner, create_session
from bokken.stages import engine_suite
from bokken.stages.base import FOUNDER
from tests.panel.test_inputs import make_repo
from tests.stages.fake_provider import ScriptedProvider


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def make_inputs(tmp_path: Path) -> dict:
    repo = make_repo(tmp_path)
    metrics = tmp_path / "kpis.csv"
    metrics.write_text("month,active_users,churn\n2026-07,1200,0.08\n")
    interview = tmp_path / "interview.md"
    interview.write_text("I stopped riding because arrivals were unpredictable.\n")
    return {
        "repo": str(repo),
        "metrics": [str(metrics)],
        "discussions": [str(interview)],
    }


def make_runner(session_dir: Path, provider: ScriptedProvider, input_port=None) -> Runner:
    factory = lambda store: ModelRouter(store, provider)  # noqa: E731
    return Runner(
        session_dir,
        engines=engine_suite(factory),
        input_port=input_port,
        kata_factory=lambda store: Kata(MVP_MOVES, store),
    )


BRIEF = {
    "problem_space": "commuter shuttle retention",
    "constraints": ["no new hardware"],
    "target_segments": ["commuters"],
    "success_criteria": ["churn below 5%"],
    "risk_tolerance": "medium",
}


def test_dojo_full_run_offline(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    session_dir = create_session(
        "dojo-e2e",
        brief=brief,
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    provider = ScriptedProvider()
    result = make_runner(session_dir, provider).run()
    assert result.halt == "completed"

    events = list(read_events(session_dir))
    state = replay(events)
    assert state.stage == "complete"

    # Evidence grounded in tangible inputs, always simulated, kinds attached.
    grounded = [
        e
        for e in events
        if e.type == "evidence.captured" and e.payload.get("grounding") == "corpus"
    ]
    assert grounded
    kinds = {c.get("source_kind") for e in grounded for c in e.payload.get("citations", [])}
    assert kinds & {"code", "metrics", "discussion"}
    assert all(e.payload["confidence_class"] == "simulated" for e in grounded)

    # Panels: interview + ideation + test manifests, firewall checked disjoint.
    manifests = {
        e.payload["panel_kind"]
        for e in events
        if e.type == "artifact.generated" and e.payload.get("kind") == "panel_manifest"
    }
    assert manifests == {"interview", "ideation", "test"}
    firewall = next(
        e
        for e in events
        if e.type == "decision.recorded" and e.payload["question"] == "contamination firewall check"
    )
    assert firewall.payload["resolution"] == "disjoint"

    # Criteria frozen before any option event.
    criteria_seq = next(
        e.seq
        for e in events
        if e.type == "decision.recorded" and e.payload["question"] == "convergence criteria"
    )
    first_option_seq = min(e.seq for e in events if e.type.startswith("option."))
    assert criteria_seq < first_option_seq

    # JTBD: outcomes derived and scored; deterministic opportunity ranking journaled.
    outcomes = [i for i in state.insights.values() if i.kind == "desired_outcome"]
    opportunities = [i for i in state.insights.values() if i.kind == "opportunity"]
    assert outcomes and opportunities
    top = next(i for i in opportunities if "plan around arrivals" in i.statement)
    assert "16" in top.statement and "severely underserved" in top.statement  # 9 + (9-2)
    ranking = next(e for e in events if e.payload.get("kind") == "opportunity_ranking")
    assert (session_dir / ranking.payload["path"]).exists()

    # Convergence: three firewalled lenses voted; the red verdict is dissent on record.
    concept = next(
        e
        for e in events
        if e.type == "decision.recorded"
        and e.payload["question"] == "which concept advances to prototype"
    )
    lens_actors = {p["actor"] for p in concept.payload["positions"]}
    assert {"feasibility", "viability", "desirability"} <= lens_actors
    assert any(
        d["actor"] == "feasibility" and "red" in d["reservation"]
        for d in concept.payload["dissent"]
    )
    statement_decision = next(
        e
        for e in events
        if e.type == "decision.recorded"
        and e.payload["question"] == "which problem statement do we take forward"
    )
    assert "opportunity coverage" in statement_decision.payload["criteria"]

    # Kata: stage contracts fired; skeptic on record; loop-back proposed on contradiction.
    executed = [e.payload["move_id"] for e in events if e.type == "facilitation.move_executed"]
    assert "stage_contract" in executed
    assert "hmw_reframe" in executed
    assert "loopback_proposal" in executed

    # Prototype: artifact on disk, hashed, mapped to assumptions.
    artifact = next(e for e in events if e.payload.get("kind") == "landing_copy")
    assert (session_dir / artifact.payload["path"]).exists()
    assert artifact.refs

    # Test: register fully scored; recommendation flags real-world validation.
    assert all(a.score is not None for a in state.assumptions.values())
    recommendation = next(
        d for d in state.decisions.values() if d.question == "kill, iterate, or proceed"
    )
    assert recommendation.resolution == "iterate"
    assert recommendation.requires_real_validation is True

    # Every model call is in the ledger with prompt provenance.
    model_calls = [e for e in events if e.type == "model.called"]
    assert model_calls and all(
        e.payload["prompt_version"].startswith("v") and e.payload["request_id"] for e in model_calls
    )
    assert state.tokens_spent() == 70 * len(model_calls)


class FounderPort:
    def __init__(self) -> None:
        self.script = [
            "arrivals were unpredictable so I quit",  # empathize answer
            "",  # ideate: no extra founder option
            "1",  # ideate: pick option 1
            "supported: the copy speaks to the pain",  # test: assumption 1
            "contradicted: nobody tolerates detours",  # test: assumption 2
        ]

    def ask(self, question: str, *, kind: str = "text") -> Answer:
        # The human at the terminal, as TerminalInputPort reports them.
        return Answer(text=self.script.pop(0), actor=FOUNDER)


def test_founder_full_run_offline(tmp_path: Path) -> None:
    session_dir = create_session("founder-e2e", brief=BRIEF, mode="founder")
    provider = ScriptedProvider()
    result = make_runner(session_dir, provider, input_port=FounderPort()).run()
    assert result.halt == "completed"

    events = list(read_events(session_dir))
    state = replay(events)
    human_evidence = [
        e for e in events if e.type == "evidence.captured" and e.actor.kind == "human"
    ]
    assert human_evidence
    assert all(e.payload["confidence_class"] in ("observed", "reported") for e in human_evidence)
    assert state.stage == "complete"
    scores = {a.score for a in state.assumptions.values()}
    assert scores == {"supported", "contradicted"}


def test_resume_mid_run_offline(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    session_dir = create_session(
        "resume-e2e",
        brief=brief,
        mode="dojo",
        gate_policy=["define"],
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    provider = ScriptedProvider()
    runner = make_runner(session_dir, provider)
    first = runner.run()
    assert first.halt == "gate_pending"
    runner.resolve_gate(resolution="approve", actor=Actor(kind="human", name="founder"))
    second = make_runner(session_dir, ScriptedProvider()).run()
    assert second.halt == "completed"
