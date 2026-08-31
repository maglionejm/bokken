"""Append-only JSONL journal store with hash chaining and single-writer locking."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import IO, Any

from bokken.journal.schema import (
    GENESIS_HASH,
    Actor,
    Event,
    Payload,
    Stage,
    compute_hash,
    new_event,
    parse_line,
)

JOURNAL_FILENAME = "journal.jsonl"
LOCK_FILENAME = ".lock"


class JournalError(Exception):
    pass


class SessionLockedError(JournalError):
    pass


class ChainBrokenError(JournalError):
    def __init__(self, seq: int, detail: str) -> None:
        self.seq = seq
        super().__init__(f"journal chain broken at seq {seq}: {detail}")


class JournalStore:
    """Single-writer, append-only event store for one session.

    Open with ``JournalStore.open(session_dir)`` for writing (acquires the
    session lock) or use the module-level :func:`read_events` for lock-free reads.
    """

    def __init__(self, session_dir: Path, lock_file: IO[bytes]) -> None:
        self.session_dir = session_dir
        self.path = session_dir / JOURNAL_FILENAME
        self._lock_file = lock_file
        self._last_seq = 0
        self._last_hash = GENESIS_HASH
        self._session_id = session_dir.name
        for event in read_events(session_dir):
            self._last_seq = event.seq
            self._last_hash = event.hash

    @classmethod
    def open(cls, session_dir: Path) -> JournalStore:
        session_dir.mkdir(parents=True, exist_ok=True)
        lock_file = (session_dir / LOCK_FILENAME).open("wb")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock_file.close()
            raise SessionLockedError(
                f"session at {session_dir} is locked by another writer"
            ) from exc
        return cls(session_dir, lock_file)

    def close(self) -> None:
        fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        self._lock_file.close()

    def __enter__(self) -> JournalStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @property
    def last_seq(self) -> int:
        return self._last_seq

    def append(
        self,
        *,
        type: str,
        stage: Stage | None,
        actor: Actor,
        payload: dict[str, Any] | Payload,
        refs: list[str] | None = None,
        ts: datetime | None = None,
    ) -> Event:
        """Validate, seal, and durably append one event. Nothing is written on error."""
        event = new_event(
            seq=self._last_seq + 1,
            session_id=self._session_id,
            type=type,
            stage=stage,
            actor=actor,
            payload=payload,
            refs=refs,
            prev_hash=self._last_hash,
            ts=ts,
        )
        line = event.model_dump_json() + "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._last_seq = event.seq
        self._last_hash = event.hash
        return event

    def events(self) -> Iterator[Event]:
        return read_events(self.session_dir)

    def verify_chain(self) -> None:
        verify_chain(self.session_dir)


def read_events(session_dir: Path) -> Iterator[Event]:
    """Stream persisted events in seq order. Lock-free; safe alongside a writer."""
    path = session_dir / JOURNAL_FILENAME
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield parse_line(line)


def verify_chain(session_dir: Path) -> None:
    """Verify seq contiguity and the hash chain; raise ChainBrokenError at the first break."""
    prev_hash = GENESIS_HASH
    expected_seq = 1
    for event in read_events(session_dir):
        if event.seq != expected_seq:
            raise ChainBrokenError(event.seq, f"expected seq {expected_seq}")
        if event.prev_hash != prev_hash:
            raise ChainBrokenError(event.seq, "prev_hash does not match prior record")
        if compute_hash(event) != event.hash:
            raise ChainBrokenError(event.seq, "record hash does not match content")
        prev_hash = event.hash
        expected_seq += 1
