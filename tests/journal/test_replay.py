from bokken.journal import GENESIS_HASH, new_event, replay
from tests.journal.conftest import AGENT, SYSTEM, created_payload, persona


class EventBuilder:
    def __init__(self) -> None:
        self.events = []
        self._prev = GENESIS_HASH

    def add(self, type: str, payload: dict, *, stage=None, actor=SYSTEM, refs=None):
        event = new_event(
            seq=len(self.events) + 1,
            session_id="s1",
            type=type,
            stage=stage,
            actor=actor,
            payload=payload,
            refs=refs,
            prev_hash=self._prev,
        )
        self.events.append(event)
        self._prev = event.hash
        return event


def build_dojo_run() -> EventBuilder:
    b = EventBuilder()
    b.add("session.created", created_payload(mode="dojo"), stage="intake")
    b.add(
        "transition.fired",
        {"from_stage": "intake", "to_stage": "empathize", "condition": "brief accepted"},
        stage="intake",
    )
    ev1 = b.add(
        "evidence.captured",
        {"content": "I bike daily", "source": "panel", "confidence_class": "simulated"},
        stage="empathize",
        actor=persona("p-1"),
    )
    b.add(
        "evidence.abstained",
        {"question": "willingness to pay?", "gap": "no pricing data in corpus"},
        stage="empathize",
        actor=persona("p-2"),
    )
    b.add(
        "transition.fired",
        {"from_stage": "empathize", "to_stage": "define", "condition": "coverage met"},
        stage="empathize",
    )
    insight = b.add(
        "interpretation.derived",
        {"kind": "insight", "statement": "commuters value predictability", "ungrounded": False},
        stage="define",
        actor=AGENT,
        refs=[ev1.id],
    )
    b.add(
        "decision.recorded",
        {
            "question": "problem statement",
            "options": ["ps-a", "ps-b"],
            "criteria": ["coverage"],
            "resolution": "ps-a",
            "dissent": [{"actor": "skeptic", "reservation": "thin evidence"}],
            "requires_real_validation": True,
        },
        stage="define",
        actor=AGENT,
        refs=[insight.id],
    )
    b.add(
        "transition.fired",
        {"from_stage": "define", "to_stage": "ideate", "condition": "statement selected"},
        stage="define",
    )
    opt_a = b.add(
        "option.created", {"summary": "shuttle pooling"}, stage="ideate", actor=persona("p-1")
    )
    opt_b = b.add(
        "option.built_on",
        {"summary": "shuttle pooling with dynamic stops"},
        stage="ideate",
        actor=persona("p-2"),
        refs=[opt_a.id],
    )
    merged = b.add(
        "option.merged",
        {"summary": "adaptive shuttle network"},
        stage="ideate",
        actor=AGENT,
        refs=[opt_a.id, opt_b.id],
    )
    b.add(
        "option.killed",
        {"reason": "infeasible fleet size"},
        stage="ideate",
        actor=AGENT,
        refs=[merged.id],
    )
    b.add(
        "facilitation.move_executed",
        {"move_id": "devils_advocate", "trigger": "zero dissent", "params": {}},
        stage="ideate",
        actor=AGENT,
    )
    b.add(
        "facilitation.move_suppressed",
        {"move_id": "devils_advocate", "trigger": "zero dissent", "reason": "budget_exhausted"},
        stage="ideate",
        actor=AGENT,
    )
    assumption = b.add(
        "assumption.registered",
        {"statement": "riders accept 5 min detours", "impact": "high", "uncertainty": "high"},
        stage="prototype",
        actor=AGENT,
    )
    b.add(
        "assumption.scored",
        {"score": "contradicted", "rationale": "panel rejected detours"},
        stage="test",
        actor=AGENT,
        refs=[assumption.id, ev1.id],
    )
    b.add(
        "model.called",
        {
            "routing_class": "cognition",
            "model": "claude-opus-4-8",
            "prompt_id": "define/cluster",
            "prompt_version": "v1",
            "prompt_hash": "abc",
            "usage": {"input_tokens": 1000, "output_tokens": 250},
            "status": "ok",
        },
        stage="define",
        actor=AGENT,
    )
    b.add(
        "model.called",
        {
            "routing_class": "cognition",
            "model": "claude-opus-4-8",
            "prompt_id": "ideate/roundtable",
            "prompt_version": "v1",
            "prompt_hash": "def",
            "usage": {"input_tokens": 500, "output_tokens": 100},
            "status": "ok",
        },
        stage="ideate",
        actor=AGENT,
    )
    b.add(
        "artifact.generated",
        {
            "path": "artifacts/prototype/one-pager.md",
            "kind": "concept_one_pager",
            "content_hash": "h1",
        },
        stage="prototype",
        actor=AGENT,
        refs=[assumption.id],
    )
    return b


def test_full_fold() -> None:
    b = build_dojo_run()
    state = replay(b.events)
    assert state.mode == "dojo"
    assert state.stage == "ideate"
    assert state.evidence_by_class == {"simulated": 1}
    assert len(state.research_debt) == 1
    assert state.research_debt[0].question == "willingness to pay?"
    insight = next(iter(state.insights.values()))
    assert insight.refs and not insight.ungrounded
    decision = next(iter(state.decisions.values()))
    assert decision.dissent == [{"actor": "skeptic", "reservation": "thin evidence"}]
    assert decision.requires_real_validation is True
    statuses = {o.summary: o.status for o in state.options.values()}
    assert statuses["shuttle pooling"] == "merged"
    assert statuses["shuttle pooling with dynamic stops"] == "merged"
    assert statuses["adaptive shuttle network"] == "killed"
    killed = next(o for o in state.options.values() if o.status == "killed")
    assert killed.status_reason == "infeasible fleet size"
    assert state.moves_executed == {"devils_advocate": 1}
    assert state.moves_suppressed == [{"move_id": "devils_advocate", "reason": "budget_exhausted"}]
    assumption = next(iter(state.assumptions.values()))
    assert assumption.score == "contradicted"
    assert state.tokens_spent("cognition") == 1850
    assert state.tokens_spent() == 1850
    assert len(state.artifacts) == 1
    assert state.artifacts[0].refs == [assumption.id]


def test_replay_is_deterministic() -> None:
    b = build_dojo_run()
    assert replay(b.events) == replay(b.events)


def test_gate_pending_and_resolution() -> None:
    b = build_dojo_run()
    b.add(
        "session.gate_requested",
        {"gate_id": "g1", "from_stage": "ideate", "to_stage": "prototype"},
        stage="ideate",
    )
    state = replay(b.events)
    assert state.pending_gate is not None
    assert state.pending_gate.to_stage == "prototype"
    b.add(
        "session.gate_resolved",
        {"gate_id": "g1", "resolution": "approve"},
        stage="ideate",
        actor=SYSTEM,
    )
    assert replay(b.events).pending_gate is None


def test_stop_and_resume_semantics() -> None:
    b = build_dojo_run()
    b.add("session.stopped", {"reason": "budget_exhausted"}, stage="ideate")
    stopped_state = replay(b.events)
    assert stopped_state.stopped == "budget_exhausted"
    assert stopped_state.stage == "ideate"
    pre_stop_lineage = {o.id: o.status for o in stopped_state.options.values()}
    b.add("session.resumed", {}, stage="ideate")
    resumed = replay(b.events)
    assert resumed.stopped is None
    assert resumed.stage == "ideate"
    assert {o.id: o.status for o in resumed.options.values()} == pre_stop_lineage
