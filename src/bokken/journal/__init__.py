"""The Journal: Bokken's event-sourced, append-only process ledger.

Public API:

- ``schema``: event envelope, taxonomy v1, payload models, canonical hashing.
- ``store``: :class:`JournalStore` (single-writer append), lock-free reads,
  chain verification.
- ``workspace``: session directories, name resolution, listing.
- ``replay``: pure fold of a journal into :class:`SessionState`.
- ``query``: filtered reads and follow mode.
"""

from bokken.journal.query import follow, query
from bokken.journal.replay import SessionState, replay, replay_session
from bokken.journal.schema import (
    GENESIS_HASH,
    SCHEMA_VERSION,
    STAGES,
    TAXONOMY,
    Actor,
    Brief,
    BriefInputs,
    ConfidenceClass,
    Event,
    Mode,
    RoutingClass,
    Stage,
    new_event,
    parse_line,
    seal,
)
from bokken.journal.store import (
    ChainBrokenError,
    JournalError,
    JournalStore,
    SessionLockedError,
    read_events,
    verify_chain,
)
from bokken.journal.workspace import (
    SessionExistsError,
    SessionInfo,
    SessionNotFoundError,
    WorkspaceError,
    create_session_dir,
    list_sessions,
    resolve_session_dir,
    sessions_dir,
    slugify,
    workspace_root,
)

__all__ = [
    "GENESIS_HASH",
    "SCHEMA_VERSION",
    "STAGES",
    "TAXONOMY",
    "Actor",
    "Brief",
    "BriefInputs",
    "ChainBrokenError",
    "ConfidenceClass",
    "Event",
    "JournalError",
    "JournalStore",
    "Mode",
    "RoutingClass",
    "SessionExistsError",
    "SessionInfo",
    "SessionLockedError",
    "SessionNotFoundError",
    "SessionState",
    "Stage",
    "WorkspaceError",
    "create_session_dir",
    "follow",
    "list_sessions",
    "new_event",
    "parse_line",
    "query",
    "read_events",
    "replay",
    "replay_session",
    "resolve_session_dir",
    "seal",
    "sessions_dir",
    "slugify",
    "verify_chain",
    "workspace_root",
]
