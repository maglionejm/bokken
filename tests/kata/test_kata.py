from pathlib import Path

import pytest

from bokken.journal import JournalStore, replay
from bokken.kata import DEVILS_ADVOCATE_LABEL, MVP_MOVES, Kata, TriggerFire, render_move
from tests.journal.conftest import SYSTEM, created_payload

EXPECTED_MOVES = {
    "stage_contract",
    "hmw_reframe",
    "assumption_flag",
    "timebox_pivot",
    "synthesis_readback",
    "devils_advocate",
    "parking_lot",
    "loopback_proposal",
    "close_and_commit",
}


@pytest.fixture
def store(tmp_path: Path):
    with JournalStore.open(tmp_path / "kata-session") as s:
        s.append(type="session.created", stage="intake", actor=SYSTEM, payload=created_payload())
        yield s


def fresh_state(store: JournalStore):
    return replay(store.events())


def test_registry_introspection_lists_all_moves(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store)
    moves = kata.list_moves()
    assert {m.move_id for m in moves} == EXPECTED_MOVES
    for move in moves:
        assert move.intent and move.stages and move.trigger_description
        assert set(move.surfaces) == {"founder", "dojo"}


def test_move_without_signal_is_inert(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store)
    before = store.last_seq
    assert kata.evaluate("hmw_reframe", fresh_state(store), {}, stage="define") is None
    assert store.last_seq == before


def test_out_of_stage_suppression(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store)
    signals = {"novelty_rate": 0.05, "novelty_floor": 0.2}
    event = kata.evaluate("timebox_pivot", fresh_state(store), signals, stage="define")
    assert event is not None
    assert event.type == "facilitation.move_suppressed"
    assert event.payload["reason"] == "out_of_stage"


def test_execution_journals_trigger_params_and_refs(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store)
    signals = {"unsupported_claim": "2x conversion at flat spend", "refs": []}
    event = kata.evaluate("assumption_flag", fresh_state(store), signals, stage="define")
    assert event is not None and event.type == "facilitation.move_executed"
    assert event.payload["params"]["claim"] == "2x conversion at flat spend"
    assert "unvalidated" in event.payload["outcome"]


def test_budget_exhaustion_suppresses_and_survives_resume(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store, budgets={"devils_advocate": 1})
    signals = {"consensus_without_dissent": True, "counter": "segment B was never heard"}
    first = kata.evaluate("devils_advocate", fresh_state(store), signals, stage="ideate")
    assert first is not None and first.type == "facilitation.move_executed"
    second = kata.evaluate("devils_advocate", fresh_state(store), signals, stage="ideate")
    assert second is not None and second.type == "facilitation.move_suppressed"
    assert second.payload["reason"] == "budget_exhausted"

    # A fresh Kata over the same journal (a resume) still sees the spent budget.
    resumed = Kata(MVP_MOVES, store, budgets={"devils_advocate": 1})
    third = resumed.evaluate("devils_advocate", fresh_state(store), signals, stage="ideate")
    assert third is not None and third.payload["reason"] == "budget_exhausted"


def test_budget_overrides_cannot_exceed_registry_maximum(store: JournalStore) -> None:
    kata = Kata(MVP_MOVES, store, budgets={"devils_advocate": 99, "timebox_pivot": 2})
    assert kata.budget("devils_advocate") == 3  # registry maximum wins
    assert kata.budget("timebox_pivot") == 2  # tightening is allowed
    assert kata.budget("stage_contract") is None  # unlimited stays unlimited


def test_tone_contract_depersonalized_critique() -> None:
    fire = TriggerFire(trigger="t", params={"claim": "users will pay 20 EUR"})
    text = render_move("assumption_flag", fire, "dojo")
    assert "claim" in text and "unvalidated" in text
    assert "you're wrong" not in text.lower()
    assert "founder" not in text.lower()


def test_devils_advocate_is_labeled() -> None:
    fire = TriggerFire(trigger="t", params={"counter": "operators may refuse the routes"})
    text = render_move("devils_advocate", fire, "dojo")
    assert text.startswith(DEVILS_ADVOCATE_LABEL)


def test_founder_surface_adds_consent_prompt() -> None:
    fire = TriggerFire(trigger="t", params={"novelty_rate": 0.1, "floor": 0.3})
    dojo = render_move("timebox_pivot", fire, "dojo")
    founder = render_move("timebox_pivot", fire, "founder")
    assert dojo in founder and "go ahead" in founder
