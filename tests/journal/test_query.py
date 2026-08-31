import itertools
import threading

from bokken.journal import JournalStore, follow, query
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
