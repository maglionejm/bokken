import random
import string
from datetime import datetime

import pytest
from pydantic import ValidationError

from bokken.journal import GENESIS_HASH, new_event, parse_line, seal
from bokken.journal.schema import (
    TOLERANT_READ,
    Event,
    EvidenceCaptured,
    InterpretationDerived,
    SessionCreated,
    compute_hash,
)
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


def line_from_newer_writer(event: Event, **payload_extra) -> str:
    """One record as a newer Bokken that declares more payload keys would write it.

    The extra keys go in before the hash is computed, exactly as that writer's own
    (strict, but wider) validation would have produced them. This never goes
    through our write path, because our write path is meant to refuse them.
    """
    data = event.model_dump(mode="json", exclude={"hash"})
    data["payload"] = {**data["payload"], **payload_extra}
    return seal(Event.model_validate(data, context=TOLERANT_READ)).model_dump_json()


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


def test_unknown_payload_fields_tolerated_on_read() -> None:
    """A key a newer Bokken wrote survives this version's read untouched."""
    written = make("session.created", created_payload(), actor=SYSTEM, stage="intake")
    line = line_from_newer_writer(written, future_field={"nested": True})

    parsed = parse_line(line)

    assert parsed.payload["future_field"] == {"nested": True}
    assert parsed.typed_payload.model_extra == {"future_field": {"nested": True}}
    # Nothing dropped and nothing re-hashed: a read-modify-write cycle is safe.
    assert parsed.model_dump_json() == line
    assert compute_hash(parsed) == parsed.hash


def test_undeclared_payload_key_rejected_on_append() -> None:
    """The Journal is append-only, so a misspelled key must never reach it."""
    with pytest.raises(ValidationError, match="undeclared key"):
        make(
            "interpretation.derived",
            {"kind": "insight", "statement": "x", "ungrounded": True, "sevrity": "high"},
        )


def test_undeclared_nested_payload_key_rejected_on_append() -> None:
    brief = created_payload()["brief"] | {"target_segements": ["typo"]}
    with pytest.raises(ValidationError, match=r"brief\.target_segements"):
        make("session.created", created_payload() | {"brief": brief}, actor=SYSTEM, stage="intake")


def test_declared_extension_key_accepted_on_append() -> None:
    """Untyped-but-declared extension keys (EXTENSION_KEYS) still write fine."""
    event = make(
        "evidence.captured",
        {
            "content": "answer",
            "source": "persona:p-1",
            "confidence_class": "simulated",
            "segment": "commuters",
            "grounding": "corpus",
        },
        actor=persona(),
    )
    assert event.payload["segment"] == "commuters"
    assert event.extension("grounding") == "corpus"
    with pytest.raises(KeyError, match="not a declared extension key"):
        event.extension("segmnet")


def test_typed_payload_gives_attribute_access() -> None:
    event = make(
        "evidence.captured",
        {"content": "answer", "source": "doc", "confidence_class": "reported"},
        actor=HUMAN,
    )
    captured = parse_line(event.model_dump_json()).payload_as(EvidenceCaptured)
    assert captured.confidence_class == "reported"
    assert captured.speaker is None
    assert captured.citations == []


def test_payload_as_refuses_the_wrong_payload_class() -> None:
    event = make("session.created", created_payload(), actor=SYSTEM, stage="intake")
    assert event.payload_as(SessionCreated).mode == "founder"
    with pytest.raises(TypeError, match="not InterpretationDerived"):
        event.payload_as(InterpretationDerived)


def test_typed_payload_never_replaces_the_raw_mapping() -> None:
    """`Event.payload` stays the way out for generic and untyped readers."""
    event = make("session.created", created_payload(), actor=SYSTEM, stage="intake")
    assert isinstance(event.payload, dict)
    assert event.payload["brief"]["problem_space"] == "sustainable urban mobility"


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
