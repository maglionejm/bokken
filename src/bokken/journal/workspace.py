"""Session workspaces: where sessions live on disk and how names resolve."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bokken.journal.schema import Mode, Stage
from bokken.journal.store import JOURNAL_FILENAME, read_events

BOKKEN_HOME_ENV = "BOKKEN_HOME"
DEFAULT_ROOT = ".bokken"


class WorkspaceError(Exception):
    pass


class SessionExistsError(WorkspaceError):
    pass


class SessionNotFoundError(WorkspaceError):
    pass


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise WorkspaceError(f"cannot derive a session slug from {name!r}")
    return slug


def workspace_root(base: Path | None = None) -> Path:
    if base is not None:
        return base
    home = os.environ.get(BOKKEN_HOME_ENV)
    return Path(home) if home else Path.cwd() / DEFAULT_ROOT


def sessions_dir(base: Path | None = None) -> Path:
    return workspace_root(base) / "sessions"


def create_session_dir(name: str, base: Path | None = None) -> Path:
    root = sessions_dir(base)
    session_dir = root / slugify(name)
    if session_dir.exists():
        raise SessionExistsError(
            f"session '{name}' already exists at {session_dir}; use run/status instead"
        )
    session_dir.mkdir(parents=True)
    (session_dir / "artifacts").mkdir()
    return session_dir


def resolve_session_dir(name: str, base: Path | None = None) -> Path:
    session_dir = sessions_dir(base) / slugify(name)
    if not (session_dir / JOURNAL_FILENAME).exists():
        raise SessionNotFoundError(f"no session '{name}' in workspace {sessions_dir(base)}")
    return session_dir


@dataclass(frozen=True)
class SessionInfo:
    name: str
    slug: str
    stage: Stage
    mode: Mode | None
    last_ts: datetime | None


def list_sessions(base: Path | None = None) -> list[SessionInfo]:
    root = sessions_dir(base)
    if not root.exists():
        return []
    infos: list[SessionInfo] = []
    for session_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (session_dir / JOURNAL_FILENAME).exists():
            continue
        name = session_dir.name
        mode: Mode | None = None
        stage: Stage = "intake"
        last_ts: datetime | None = None
        for event in read_events(session_dir):
            last_ts = event.ts
            if event.type == "session.created":
                name = event.payload.get("name", name)
                mode = event.payload.get("mode")
            elif event.type == "transition.fired":
                stage = event.payload["to_stage"]
        infos.append(
            SessionInfo(name=name, slug=session_dir.name, stage=stage, mode=mode, last_ts=last_ts)
        )
    return infos
