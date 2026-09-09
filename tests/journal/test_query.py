import itertools
import threading
import time

import pytest

from bokken.journal import JournalStore, follow, new_event, query
from tests.journal.conftest import AGENT, HUMAN


def seed(store: JournalStore) -> None:
    store.append(
        type="evidence.captured",
        stage="empathize",
        actor=HUMAN,
        payload={"content": "note", "source": "interview", "confidence_class": "observed"},
    )
    a = store.append(
        type="option.created", stage="ideate", actor=AGENT, payload={"summary": "idea a"}
    )
    store.append(
        type="option.built_on",
        stage="ideate",
        actor=AGENT,
        payload={"summary": "idea a+"},
        refs=[a.id],
    )


def test_family_and_stage_filter(store: JournalStore) -> None:
    seed(store)
    events = list(query(store.session_dir, type="option", stage="ideate"))
    assert [e.type for e in events] == ["option.created", "option.built_on"]
    assert [e.seq for e in events] == sorted(e.seq for e in events)


def test_exact_type_actor_and_limit_filters(store: JournalStore) -> None:
    seed(store)
    assert [e.type for e in query(store.session_dir, type="evidence.captured")] == [
        "evidence.captured"
    ]
    assert all(e.actor.kind == "agent" for e in query(store.session_dir, actor="agent"))
    assert len(list(query(store.session_dir, type="option.*", limit=1))) == 1


def test_typoed_exact_type_filter_raises(store: JournalStore) -> None:
    seed(store)
    with pytest.raises(ValueError, match=r"evidence\.catpured"):
        list(query(store.session_dir, type="evidence.catpured"))


def test_since_seq_filter(store: JournalStore) -> None:
    seed(store)
    events = list(query(store.session_dir, since_seq=3))
    assert [e.seq for e in events] == [3, 4]


def test_follow_streams_new_events(store: JournalStore) -> None:
    seed(store)
    stop = threading.Event()
    received: list = []

    def consume() -> None:
        gen = follow(store.session_dir, poll_interval=0.01, stop=stop)
        received.extend(itertools.islice(gen, 5))

    t = threading.Thread(target=consume)
    t.start()
    late = store.append(
        type="option.created", stage="ideate", actor=AGENT, payload={"summary": "late idea"}
    )
    t.join(timeout=5)
    stop.set()
    assert [e.seq for e in received] == [1, 2, 3, 4, 5]
    assert received[-1].id == late.id


def test_follow_recovers_from_an_append_rollback(store: JournalStore) -> None:
    """The store truncates its own failed append; a follower whose offset now
    sits past EOF must reset instead of reading mid-record, and must not
    re-yield seqs it already surfaced."""
    e2 = store.append(
        type="evidence.captured",
        stage="empathize",
        actor=HUMAN,
        payload={"content": "note", "source": "interview", "confidence_class": "observed"},
    )
    # A deliberately huge record: after its rollback the file stays smaller
    # than the follower's stale offset no matter when the follower polls, so
    # the shrink is always observed and the test cannot race.
    store.append(
        type="option.created", stage="ideate", actor=AGENT, payload={"summary": "x" * 20_000}
    )
    stop = threading.Event()
    received: list = []

    def consume() -> None:
        gen = follow(store.session_dir, poll_interval=0.01, stop=stop)
        received.extend(itertools.islice(gen, 4))

    t = threading.Thread(target=consume)
    t.start()
    try:
        deadline = time.monotonic() + 5
        while len(received) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(received) == 3
        # Roll back the last append exactly as the store does on a failed
        # fsync: truncate the file to just before the final record ...
        lines = store.path.read_text(encoding="utf-8").splitlines(keepends=True)
        with store.path.open("rb+") as f:
            f.truncate(sum(len(line.encode("utf-8")) for line in lines[:-1]))
        # ... then append a replacement at the same seq plus one genuinely new
        # record, as a retried writer would.
        session_id = received[0].session_id
        replacement = new_event(
            seq=3,
            session_id=session_id,
            type="option.created",
            stage="ideate",
            actor=AGENT,
            payload={"summary": "replacement idea after the rollback"},
            prev_hash=e2.hash,
        )
        fresh = new_event(
            seq=4,
            session_id=session_id,
            type="option.created",
            stage="ideate",
            actor=AGENT,
            payload={"summary": "post-rollback idea"},
            prev_hash=replacement.hash,
        )
        with store.path.open("a", encoding="utf-8") as f:
            f.write(replacement.model_dump_json() + "\n" + fresh.model_dump_json() + "\n")
        t.join(timeout=5)
        assert not t.is_alive()
        # No crash, no duplicate seqs: the replacement seq 3 is skipped (its
        # rolled-back predecessor was already surfaced) and only the genuinely
        # new record is yielded.
        assert [e.seq for e in received] == [1, 2, 3, 4]
        assert received[3].id == fresh.id
    finally:
        stop.set()
        t.join(timeout=5)
