"""Cross-run diff: pure derivation over two finalized runs of one product."""

from __future__ import annotations

from pathlib import Path

import pytest

from bokken.contract import DiffResult, diff_result
from bokken.diffing import DiffRefused, diff_sessions
from bokken.journal import Actor, JournalStore, read_events
from bokken.orchestrator import create_session
from tests.stages.test_engines_e2e import BRIEF, make_inputs


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


FACILITATOR = Actor(kind="agent", name="facilitator")
EXPLORER = Actor(kind="agent", name="code-explorer")
PERSONA = Actor(kind="agent", name="Marta", persona_id="p-1")


def _make_session(name: str, *, brief: dict, mode: str = "dojo") -> Path:
    return create_session(
        name, brief=brief, mode=mode, gate_policy="none", config_extra={"panel": {"size": 6}}
    )


def _evidence(store: JournalStore, content: str, confidence_class: str = "simulated"):
    # Persona utterances must be simulated; a non-persona actor may report
    # grounded (e.g. code-exploration) evidence.
    if confidence_class == "simulated":
        actor, payload = PERSONA, {"speaker": "Marta", "source": "panel interview"}
    else:
        actor, payload = EXPLORER, {"source": "code exploration"}
    return store.append(
        type="evidence.captured",
        stage="empathize",
        actor=actor,
        payload={"content": content, "confidence_class": confidence_class, **payload},
    )


def _opportunity(
    store: JournalStore, statement: str, score: float, band: str, *, actor=FACILITATOR
):
    # Ground the interpretation on evidence so the write-time honesty check
    # passes without forcing `ungrounded`.
    ev = _evidence(store, f"backing evidence for {statement}")
    return store.append(
        type="interpretation.derived",
        stage="empathize",
        actor=actor,
        payload={"kind": "opportunity", "statement": statement, "score": score, "band": band},
        refs=[ev.id],
    )


def _capability(store: JournalStore, statement: str, *, ungrounded: bool = False):
    refs = []
    if not ungrounded:
        refs = [_evidence(store, f"code shows {statement}", "reported").id]
    return store.append(
        type="interpretation.derived",
        stage="empathize",
        actor=EXPLORER,
        payload={"kind": "current_capability", "statement": statement, "ungrounded": ungrounded},
        refs=refs,
    )


def _assumption(store: JournalStore, statement: str, score: str | None = None):
    reg = store.append(
        type="assumption.registered",
        stage="prototype",
        actor=FACILITATOR,
        payload={"statement": statement, "impact": "high", "uncertainty": "high"},
    )
    if score is not None:
        store.append(
            type="assumption.scored",
            stage="test",
            actor=FACILITATOR,
            payload={"score": score},
            refs=[reg.id],
        )
    return reg


def _verdict(
    store: JournalStore,
    resolution: str,
    *,
    actor: Actor = FACILITATOR,
    requires_real_validation: bool = False,
):
    store.append(
        type="decision.recorded",
        stage="test",
        actor=actor,
        payload={
            "question": "kill, iterate, or proceed",
            "options": ["kill", "iterate", "proceed"],
            "criteria": ["assumption register scores"],
            "positions": [],
            "resolution": resolution,
            "dissent": [],
            "requires_real_validation": requires_real_validation,
        },
    )


def _finalize(store: JournalStore):
    # Drive the state machine to `complete` so the model reports status complete.
    store.append(
        type="transition.fired",
        stage="test",
        actor=FACILITATOR,
        payload={"from_stage": "test", "to_stage": "complete", "condition": "run complete"},
    )


def _build(name: str, *, brief: dict, mode: str = "dojo", populate=lambda store: None) -> Path:
    session_dir = _make_session(name, brief=brief, mode=mode)
    with JournalStore.open(session_dir) as store:
        populate(store)
        _finalize(store)
    return session_dir


# --- 1.1 pure derivation: no writes, no model calls -------------------------


def test_diff_makes_no_model_calls_and_does_not_touch_journals(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def base(store):
        _opportunity(store, "O0: know arrival time", 12.0, "underserved")
        _verdict(store, "iterate")

    old = _build("diff-old", brief=brief, populate=base)
    new = _build("diff-new", brief=brief, populate=base)

    old_bytes = (old / "journal.jsonl").read_bytes()
    new_bytes = (new / "journal.jsonl").read_bytes()
    calls_before = sum(1 for d in (old, new) for e in read_events(d) if e.type == "model.called")

    diff_sessions(old, new)

    assert (old / "journal.jsonl").read_bytes() == old_bytes  # byte-identical
    assert (new / "journal.jsonl").read_bytes() == new_bytes
    calls_after = sum(1 for d in (old, new) for e in read_events(d) if e.type == "model.called")
    assert calls_after == calls_before == 0


# --- 1.2 preconditions ------------------------------------------------------


def test_unfinalized_session_is_refused(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    done = _build("done-run", brief=brief, populate=lambda s: _verdict(s, "iterate"))
    inflight = _make_session("in-flight-run", brief=brief)  # never finalized

    with pytest.raises(DiffRefused) as exc:
        diff_sessions(done, inflight)
    assert "in-flight-run" in str(exc.value) and "not finalized" in str(exc.value)


def test_product_mismatch_by_repo_is_refused(tmp_path: Path) -> None:
    inputs_a = make_inputs(tmp_path / "a")
    inputs_b = make_inputs(tmp_path / "b")
    a = _build("app-alpha", brief={**BRIEF, "inputs": inputs_a}, populate=lambda s: None)
    b = _build("app-beta", brief={**BRIEF, "inputs": inputs_b}, populate=lambda s: None)

    with pytest.raises(DiffRefused) as exc:
        diff_sessions(a, b)
    assert "not the same product" in str(exc.value)


def test_product_mismatch_by_problem_space_is_refused() -> None:
    a = _build("ps-alpha", brief={**BRIEF, "problem_space": "shuttle retention"})
    b = _build("ps-beta", brief={**BRIEF, "problem_space": "grocery delivery"})

    with pytest.raises(DiffRefused) as exc:
        diff_sessions(a, b)
    assert "not the same product" in str(exc.value)


# --- 1.3 opportunity re-ranking ---------------------------------------------


def test_opportunity_reranked_added_and_dropped(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def old(store):
        _opportunity(store, "O0: know arrival time", 12.0, "underserved")
        _opportunity(store, "O1: fewer transfers", 8.0, "appropriately served")  # dropped

    def new(store):
        _opportunity(store, "O0: know arrival time", 16.0, "severely underserved")  # re-ranked
        _opportunity(store, "O2: pre-book seats", 10.0, "underserved")  # added

    data = diff_sessions(
        _build("op-old", brief=brief, populate=old),
        _build("op-new", brief=brief, populate=new),
    )
    by_run = {(o.run, o.statement): o for o in data.opportunities}

    reranked = by_run[("both", "O0: know arrival time")]
    assert reranked.old_score == 12.0 and reranked.new_score == 16.0
    assert reranked.score_delta == 4.0
    assert reranked.old_band == "underserved" and reranked.new_band == "severely underserved"

    added = by_run[("new", "O2: pre-book seats")]
    assert added.new_score == 10.0 and added.old_score is None

    dropped = by_run[("old", "O1: fewer transfers")]
    assert dropped.old_score == 8.0 and dropped.new_score is None


# --- 1.4 assumption flips ---------------------------------------------------


def test_assumption_flip_unchanged_and_added(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def old(store):
        _assumption(store, "riders will pre-book", "untested")
        _assumption(store, "honesty reduces churn", "supported")  # unchanged -> no row

    def new(store):
        _assumption(store, "riders will pre-book", "supported")  # flip
        _assumption(store, "honesty reduces churn", "supported")
        _assumption(store, "commuters want alerts", "supported")  # added

    data = diff_sessions(
        _build("as-old", brief=brief, populate=old),
        _build("as-new", brief=brief, populate=new),
    )
    by_statement = {a.statement: a for a in data.assumptions}

    flip = by_statement["riders will pre-book"]
    assert flip.run == "both" and flip.old_score == "untested" and flip.new_score == "supported"
    assert "honesty reduces churn" not in by_statement  # unchanged is silent
    added = by_statement["commuters want alerts"]
    assert added.run == "new" and added.new_score == "supported"


# --- 1.5 capabilities + verdict ---------------------------------------------


def test_capability_added_and_verdict_iterate_to_proceed(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def old(store):
        _capability(store, "record a note")
        _verdict(store, "iterate")

    def new(store):
        _capability(store, "record a note")
        _capability(store, "export a CSV")  # added
        _verdict(store, "proceed")

    data = diff_sessions(
        _build("cap-old", brief=brief, populate=old),
        _build("cap-new", brief=brief, populate=new),
    )
    caps = {c.statement: c for c in data.capabilities}
    assert caps["export a CSV"].change == "added" and caps["export a CSV"].run == "new"
    assert "record a note" not in caps  # present in both, unchanged

    assert data.verdict is not None
    assert data.verdict.old_verdict == "iterate" and data.verdict.new_verdict == "proceed"
    assert data.verdict.changed is True


# --- 1.6 honesty carried, never re-derived ----------------------------------


def test_dojo_rows_stay_synthetic_founder_reads_real(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def dojo_pop(store):
        # An opportunity grounded only in simulated evidence stays synthetic.
        ev = store.append(
            type="evidence.captured",
            stage="empathize",
            actor=PERSONA,
            payload={
                "content": "arrivals are unpredictable",
                "source": "panel interview",
                "confidence_class": "simulated",
                "speaker": "Marta",
            },
        )
        store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=FACILITATOR,
            payload={
                "kind": "opportunity",
                "statement": "O0: arrival time",
                "score": 16.0,
                "band": "severely underserved",
            },
            refs=[ev.id],
        )
        _assumption(store, "riders will pre-book", "untested")
        _verdict(store, "iterate")

    old = _build("hon-old", brief=brief, mode="dojo", populate=dojo_pop)
    new = _build("hon-new", brief=brief, mode="dojo", populate=dojo_pop)
    dojo = diff_sessions(old, new)
    assert all(o.confidence_class == "simulated" for o in dojo.opportunities)
    assert all(a.confidence_class == "simulated" for a in dojo.assumptions)
    assert dojo.verdict.old_confidence_class == "simulated"

    # A founder run reading real testimony is not laundered into synthetic:
    # a human-authored verdict with no simulated backing reads `reported`, and
    # an assumption scored on real (reported) testimony reads `reported` too.
    founder_actor = Actor(kind="human", name="founder")

    def founder_pop(store):
        ev = store.append(
            type="evidence.captured",
            stage="test",
            actor=founder_actor,
            payload={
                "content": "we validated pre-booking with 12 riders",
                "source": "validation interview",
                "confidence_class": "reported",
            },
        )
        _assumption(store, "riders will pre-book", "supported")
        store.append(
            type="assumption.scored",
            stage="test",
            actor=founder_actor,
            payload={"score": "supported"},
            refs=[ev.id],
        )
        _verdict(store, "proceed", actor=founder_actor)

    f_old = _build("fon-old", brief=brief, mode="founder", populate=founder_pop)
    f_new = _build("fon-new", brief=brief, mode="founder", populate=founder_pop)
    founder = diff_sessions(f_old, f_new)
    assert founder.verdict.old_confidence_class == "reported"
    assert all(a.confidence_class == "reported" for a in founder.assumptions)


def test_founder_model_authored_verdict_reads_simulated_not_reported(tmp_path: Path) -> None:
    # Regression: a FOUNDER run whose verdict was authored by a model call (the
    # facilitator) — or backed by simulated material — must NOT be laundered into
    # `reported` just because the run isn't dojo. The honesty class comes from the
    # source decision record's provenance (actor kind / requires_real_validation),
    # and the same for an assumption scored on simulated evidence.
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def _sim_scored(store, statement, score):
        # An assumption scored against simulated (persona) evidence -> simulated.
        sim = _evidence(store, f"personas think {statement}", "simulated")
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
            refs=[reg.id, sim.id],
        )

    def founder_pop(store):
        _sim_scored(store, "riders will pre-book", "untested")
        # Verdict authored by the facilitator (a model call): model-authored.
        _verdict(store, "proceed", actor=FACILITATOR, requires_real_validation=True)

    def founder_pop_new(store):
        _sim_scored(store, "riders will pre-book", "supported")  # flip -> a "both" row
        _verdict(store, "kill", actor=FACILITATOR, requires_real_validation=True)

    data = diff_sessions(
        _build("mv-old", brief=brief, mode="founder", populate=founder_pop),
        _build("mv-new", brief=brief, mode="founder", populate=founder_pop_new),
    )

    # In the DiffData (the table's source): verdict + the simulated-backed
    # assumption both read simulated, never reported.
    assert data.verdict is not None
    assert data.verdict.old_confidence_class == "simulated"
    assert data.verdict.new_confidence_class == "simulated"
    by_statement = {a.statement: a for a in data.assumptions}
    assert by_statement["riders will pre-book"].confidence_class == "simulated"

    # And through the --json contract, unchanged.
    result = diff_result(data)
    assert result.verdict is not None
    assert result.verdict.old_confidence_class == "simulated"
    assert result.verdict.new_confidence_class == "simulated"
    assert all(a.confidence_class == "simulated" for a in result.assumptions)


def test_reworded_statement_whitespace_is_a_change_not_add_drop(tmp_path: Path) -> None:
    # Low-severity hardening: surrounding whitespace must not turn one statement
    # into a false add+drop. Matching strips (never case-folds) the key.
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def old(store):
        _assumption(store, "riders will pre-book", "untested")

    def new(store):
        _assumption(store, "  riders will pre-book  ", "supported")  # same, padded

    data = diff_sessions(
        _build("ws-old", brief=brief, populate=old),
        _build("ws-new", brief=brief, populate=new),
    )
    runs = sorted(a.run for a in data.assumptions)
    assert runs == ["both"]  # one flip row, not a "new" + "old" pair
    assert data.assumptions[0].old_score == "untested"
    assert data.assumptions[0].new_score == "supported"


# --- 2.1 contract round-trip ------------------------------------------------


def test_diff_result_round_trips_and_carries_provenance(tmp_path: Path) -> None:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}

    def old(store):
        _opportunity(store, "O0: arrival time", 12.0, "underserved")
        _assumption(store, "riders will pre-book", "untested")
        _capability(store, "record a note")
        _verdict(store, "iterate")

    def new(store):
        _opportunity(store, "O0: arrival time", 16.0, "severely underserved")
        _assumption(store, "riders will pre-book", "supported")
        _capability(store, "record a note")
        _capability(store, "export a CSV")
        _verdict(store, "proceed")

    data = diff_sessions(
        _build("ct-old", brief=brief, populate=old),
        _build("ct-new", brief=brief, populate=new),
    )
    result = diff_result(data)
    assert result.kind == "diff"

    restored = DiffResult.model_validate_json(result.model_dump_json())
    assert restored == result
    for row in (*restored.opportunities, *restored.assumptions, *restored.capabilities):
        assert row.run in ("both", "new", "old")
        assert row.confidence_class
    assert restored.verdict is not None and restored.verdict.changed is True
