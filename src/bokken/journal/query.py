"""Ledger queries: filtered reads and follow mode."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from bokken.journal.schema import TAXONOMY, ActorKind, Event, Stage, parse_line
from bokken.journal.store import JOURNAL_FILENAME, read_events


def _type_matches(event_type: str, spec: str) -> bool:
    spec = spec.removesuffix(".*").rstrip(".")
    if spec in TAXONOMY:
        return event_type == spec
    return event_type.split(".", 1)[0] == spec


def query(
    session_dir: Path,
    *,
    type: str | None = None,
    stage: Stage | None = None,
    actor: ActorKind | None = None,
    since_seq: int | None = None,
    until_seq: int | None = None,
    since_ts: datetime | None = None,
    limit: int | None = None,
) -> Iterator[Event]:
    """Filtered read over the ledger, in seq order."""
    count = 0
    for event in read_events(session_dir):
        if type is not None and not _type_matches(event.type, type):
            continue
        if stage is not None and event.stage != stage:
            continue
        if actor is not None and event.actor.kind != actor:
            continue
        if since_seq is not None and event.seq < since_seq:
            continue
        if until_seq is not None and event.seq > until_seq:
            continue
        if since_ts is not None and event.ts < since_ts:
            continue
        yield event
        count += 1
        if limit is not None and count >= limit:
            return


def follow(
    session_dir: Path,
    *,
    since_seq: int = 0,
    poll_interval: float = 0.2,
    stop: threading.Event | None = None,
) -> Iterator[Event]:
    """Yield existing events past ``since_seq``, then new ones as they are appended.

    Runs until ``stop`` is set (or forever if no stop event is given).
    New events are read incrementally from the file offset, not by re-reading.
    """
    path = session_dir / JOURNAL_FILENAME
    offset = 0
    buffer = ""
    while stop is None or not stop.is_set():
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                f.seek(offset)
                chunk = f.read()
                offset = f.tell()
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    event = parse_line(line)
                    if event.seq > since_seq:
                        yield event
        if stop is not None and stop.is_set():
            return
        time.sleep(poll_interval)
