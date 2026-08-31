import random
import string
from datetime import datetime

import pytest
from pydantic import ValidationError

from bokken.journal import GENESIS_HASH, new_event, parse_line, seal
from bokken.journal.schema import Event, compute_hash
from tests.journal.conftest import AGENT, HUMAN, SYSTEM, created_payload, persona


def make(type: str, payload: dict, actor=AGENT, stage="empathize", refs=None, **kw):
    return new_event(
        seq=kw.get("seq", 1),
        session_id="s1",
        type=type,
        stage=stage,
        actor=actor,
        payload=payload,
        refs=refs,
        prev_hash=kw.get("prev_hash", GENESIS_HASH),
    )


def test_valid_event_round_trips() -> None:
    event = make("session.created", created_payload(), actor=SYSTEM, stage="intake")
    line = event.model_dump_json()
    parsed = parse_line(line)
    assert parsed == event
    assert parsed.model_dump_json() == line


def test_missing_envelope_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Event.model_validate({"seq": 1, "type": "session.resumed"})


def test_unknown_stage_rejected() -> None:
    with pytest.raises(ValidationError):
        make("session.resumed", {}, stage="canvas")


def test_non_utc_timestamp_rejected() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        Event(
            seq=1,
            id="x",
            ts=datetime(2026, 8, 31, 12, 0, 0),  # naive
            session_id="s1",
            type="session.resumed",
            stage=None,
            actor=SYSTEM,
            payload={},
            prev_hash=GENESIS_HASH,
        )


def test_unknown_event_type_rejected() -> None:
    with pytest.raises(ValidationError, match=r"canvas\.drawn"):
        make("canvas.drawn", {})


def test_unknown_payload_fields_tolerated() -> None:
    payload = created_payload() | {"future_field": {"nested": True}}
    event = make("session.created", payload, actor=SYSTEM, stage="intake")
    parsed = parse_line(event.model_dump_json())
    assert parsed.payload["future_field"] == {"nested": True}


def test_persona_evidence_must_be_simulated() -> None:
    with pytest.raises(ValidationError, match="simulated"):
        make(
            "evidence.captured",
            {"content": "answer", "source": "interview", "confidence_class": "observed"},
            actor=persona(),
        )


def test_human_evidence_cannot_be_simulated() -> None:
    with pytest.raises(ValidationError, match="simulated"):
        make(
            "evidence.captured",
            {"content": "answer", "source": "interview", "confidence_class": "simulated"},
            actor=HUMAN,
        )


def test_interpretation_without_refs_requires_ungrounded_flag() -> None:
    with pytest.raises(ValidationError, match="ungrounded"):
        make("interpretation.derived", {"kind": "insight", "statement": "x", "ungrounded": False})
    ok = make("interpretation.derived", {"kind": "insight", "statement": "x", "ungrounded": True})
    assert ok.payload["ungrounded"] is True


def test_gate_rejection_requires_reason() -> None:
    with pytest.raises(ValidationError, match="reason"):
        make("session.gate_resolved", {"gate_id": "g1", "resolution": "reject"}, actor=HUMAN)


def test_refs_required_for_lineage_mutations() -> None:
    with pytest.raises(ValidationError, match="refs"):
        make("option.killed", {"reason": "dominated"})


def test_decision_preserves_dissent_verbatim() -> None:
    event = make(
        "decision.recorded",
        {
            "question": "which problem statement",
            "options": ["a", "b"],
            "criteria": ["evidence coverage"],
            "resolution": "a",
            "dissent": [{"actor": "skeptic", "reservation": "segment B unheard"}],
        },
        stage="define",
    )
    parsed = parse_line(event.model_dump_json())
    assert parsed.payload["dissent"] == [{"actor": "skeptic", "reservation": "segment B unheard"}]


def test_hash_round_trip_property() -> None:
    rng = random.Random(7)
    prev = GENESIS_HASH
    for seq in range(1, 40):
        content = "".join(rng.choices(string.printable, k=rng.randint(1, 200)))
        event = make(
            "evidence.captured",
            {"content": content, "source": "doc", "confidence_class": "reported"},
            actor=HUMAN,
            seq=seq,
            prev_hash=prev,
        )
        parsed = parse_line(event.model_dump_json())
        assert compute_hash(parsed) == event.hash
        assert seal(parsed).hash == event.hash
        prev = event.hash
