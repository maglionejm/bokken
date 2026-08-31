import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from bokken.journal import (
    ChainBrokenError,
    JournalStore,
    SessionExistsError,
    SessionLockedError,
    SessionNotFoundError,
    create_session_dir,
    list_sessions,
    read_events,
    resolve_session_dir,
    verify_chain,
)
from tests.journal.conftest import HUMAN, SYSTEM, created_payload


def append_evidence(store: JournalStore, content: str):
    return store.append(
        type="evidence.captured",
        stage="empathize",
        actor=HUMAN,
        payload={"content": content, "source": "interview", "confidence_class": "observed"},
    )


def test_append_assigns_contiguous_seq_and_reads_back(store: JournalStore) -> None:
    e2 = append_evidence(store, "first")
    e3 = append_evidence(store, "second")
    events = list(store.events())
    assert [e.seq for e in events] == [1, 2, 3]
    assert events[1] == e2 and events[2] == e3
    lines = (store.path).read_text().splitlines()
    assert lines[1] == e2.model_dump_json()


def test_chain_verifies_and_detects_tampering(store: JournalStore) -> None:
    append_evidence(store, "first")
    append_evidence(store, "second")
    store.verify_chain()
    lines = store.path.read_text().splitlines()
    record = json.loads(lines[1])
    record["payload"]["content"] = "altered"
    lines[1] = json.dumps(record)
    store.path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ChainBrokenError) as exc:
        verify_chain(store.session_dir)
    assert exc.value.seq == 2


def test_second_writer_is_refused(store: JournalStore) -> None:
    with pytest.raises(SessionLockedError):
        JournalStore.open(store.session_dir)


def test_workspace_create_resolve_and_duplicate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    session_dir = create_session_dir("Mars Lander")
    assert session_dir == tmp_path / "home" / "sessions" / "mars-lander"
    with JournalStore.open(session_dir) as store:
        store.append(
            type="session.created",
            stage="intake",
            actor=SYSTEM,
            payload=created_payload(name="Mars Lander", mode="dojo"),
        )
    assert resolve_session_dir("mars lander") == session_dir
    with pytest.raises(SessionExistsError):
        create_session_dir("mars-lander")
    with pytest.raises(SessionNotFoundError):
        resolve_session_dir("nope")
    infos = list_sessions()
    assert len(infos) == 1
    assert infos[0].name == "Mars Lander"
    assert infos[0].mode == "dojo"
    assert infos[0].stage == "intake"


CRASH_SCRIPT = textwrap.dedent(
    """
    import sys
    from bokken.journal import Actor, JournalStore
    store = JournalStore.open(__import__("pathlib").Path(sys.argv[1]))
    actor = Actor(kind="human", name="founder")
    i = 0
    while True:
        i += 1
        store.append(
            type="evidence.captured",
            stage="empathize",
            actor=actor,
            payload={"content": f"note {i}", "source": "interview", "confidence_class": "observed"},
        )
    """
)


def test_killed_writer_leaves_verifiable_journal(tmp_path: Path) -> None:
    session_dir = tmp_path / "crash-session"
    session_dir.mkdir()
    proc = subprocess.Popen(
        [sys.executable, "-c", CRASH_SCRIPT, str(session_dir)],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    deadline = time.monotonic() + 10
    journal = session_dir / "journal.jsonl"
    while time.monotonic() < deadline:
        if journal.exists() and journal.stat().st_size > 2000:
            break
        time.sleep(0.05)
    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=10)
    events = list(read_events(session_dir))
    assert len(events) > 0
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    verify_chain(session_dir)
    # The session must be reopenable for writing after the crash.
    with JournalStore.open(session_dir) as store:
        assert store.last_seq == len(events)
