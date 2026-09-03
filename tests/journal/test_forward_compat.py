"""Sessions written before the typed read path must still load, replay and verify.

`fixtures/legacy-session/journal.jsonl` was produced by the code as it stood
before `Event.typed_payload` and the strict write path existed. It is committed
verbatim and must never be regenerated: its value is precisely that nothing in
this repository can quietly change it. It carries, on purpose,

- a payload key no version of Bokken declares (`session.created.future_field`),
- the extension keys real producers write (`segment`, `grounding`, `panel_kind`,
  `requested_model`, `config_overrides`, `private_thought`, ...),
- an `interpretation.derived` record with two misspelled keys that the tolerant
  write path accepted before it was made strict, and which are now immortal,
- an `evidence.captured` record written without `speaker` or `citations`, so the
  declared defaults the old writer materialized into the record are locked in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bokken.journal import read_events, replay, verify_chain
from bokken.journal.schema import (
    EvidenceCaptured,
    InterpretationDerived,
    SessionCreated,
    compute_hash,
)

FIXTURE = Path(__file__).parent / "fixtures" / "legacy-session"


@pytest.fixture(scope="module")
def legacy_events() -> list:
    return list(read_events(FIXTURE))


def test_legacy_chain_still_verifies() -> None:
    """The guard against schema drift: a payload model that gained a defaulted
    field would inject that default on read, change every recomputed hash, and
    lock the operator out of their own session. This test fails first."""
    verify_chain(FIXTURE)


def test_legacy_record_hashes_are_unchanged(legacy_events: list) -> None:
    for event in legacy_events:
        assert compute_hash(event) == event.hash, f"seq {event.seq} re-hashed differently"


def test_legacy_journal_still_replays(legacy_events: list) -> None:
    state = replay(legacy_events)
    assert state.mode == "dojo"
    assert state.stage == "empathize"
    assert state.evidence_by_class == {"simulated": 1, "reported": 1}
    assert [item.segment for item in state.evidence.values()] == ["commuters", "commuters"]
    assert state.config["budgets"] == {"cognition": 5000}  # applied from session.resumed


def test_legacy_undeclared_keys_survive_a_read(legacy_events: list) -> None:
    created = legacy_events[0]
    assert created.payload["future_field"] == {"nested": True}
    assert created.typed_payload.model_extra == {"future_field": {"nested": True}}


def test_legacy_typo_is_read_back_not_rejected(legacy_events: list) -> None:
    """Reads never reject: a typo already on disk is a fact about the record."""
    derived = next(e for e in legacy_events if e.type == "interpretation.derived")
    typed = derived.payload_as(InterpretationDerived)
    assert typed.statement.startswith("riders abandon the app")
    assert typed.model_extra == {"sevrity": "high", "confidence": "totally made up"}


def test_legacy_defaults_materialized_by_the_old_writer(legacy_events: list) -> None:
    founder = [e for e in legacy_events if e.type == "evidence.captured"][1]
    assert "speaker" in founder.payload and founder.payload["speaker"] is None
    typed = founder.payload_as(EvidenceCaptured)
    assert typed.confidence_class == "reported"
    assert typed.citations == []


def test_legacy_brief_reads_through_the_nested_typed_payload(legacy_events: list) -> None:
    created = legacy_events[0].payload_as(SessionCreated)
    assert created.brief.problem_space == "sustainable urban mobility"
    assert created.brief.target_segments == ["commuters"]
    assert created.brief.allow_web_research is False
    assert created.config == {"demo": True}
