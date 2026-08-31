# Design: add-journal-ledger

## Context

Greenfield. See proposal.md for motivation. Constraints that shape the design: crash-safety without a database, human-inspectable storage (a consultant must be able to `cat` the ledger), single-writer sessions on a local filesystem, and "keep it light" (stdlib before dependencies).

## Goals / Non-Goals

**Goals:**

- One obvious write path (`JournalStore.append`) and one obvious read path (replay/query) for every other capability.
- Zero-infrastructure durability: a laptop and a filesystem are enough.
- Schema evolution without breaking old journals (tolerant reader).

**Non-Goals:**

- Multi-writer concurrency, remote/shared storage, W3C-PROV export (Blueprint's "native/scale path" — later horizon).
- Encryption at rest (session data lives in the user's own workspace).
- SQLite index — revisit only if query latency on real journals demands it.

## Decisions

1. **JSONL over SQLite** — append-only JSONL is human-readable, trivially crash-safe (line-atomic writes + fsync), diffable, and greppable. SQLite adds a dependency surface and hides the ledger from inspection. Alternative considered: SQLite WAL — rejected for MVP as heavier with no current query-scale need.
2. **Pydantic v2 models per event type, discriminated by `type`** — validation at the append boundary, `model_dump_json()` for canonical serialization. Alternative: dataclasses + hand-rolled validation — rejected; pydantic is already a dependency and gives forward-compat (`model_config = ConfigDict(extra="allow")` on payloads) for free.
3. **Event `id` = `uuid4` hex; ordering comes from `seq`, not from the id** — avoids a ULID dependency. `seq` is authoritative for order; `id` is only for cross-references (`refs`).
4. **Hash chain: SHA-256 over canonical JSON (sorted keys, no whitespace) of the record minus `hash`** — stdlib `hashlib`/`json`. Genesis `prev_hash` is `"0" * 64`. This is tamper-*evidence*, not tamper-*proofing* — good enough for audit honesty claims.
5. **Locking via `fcntl.flock` on a `.lock` file in the session dir** — stdlib, adequate for the single-machine, single-writer model. Alternative: pid files — rejected (stale-pid races).
6. **Replay as a pure fold** — `replay(events) -> SessionState` with no I/O inside the fold; the store streams events into it. Keeps replay deterministic and unit-testable with synthetic event lists.
7. **Follow mode via polling the file offset (0.2 s tick)** — stdlib-only; inotify/kqueue variants are platform-specific complexity the MVP doesn't need.

## Risks / Trade-offs

- [Journal grows unbounded for very long Dojo runs] → payloads store artifact *references* (path + hash), never large blobs; artifacts live in `artifacts/`.
- [Canonical-JSON drift between writers would break the chain] → single canonicalization function owned by the journal module; property test: serialize → hash → parse → re-hash equality.
- [Schema v1 freeze pressure from downstream changes] → the taxonomy includes a generous payload envelope per family; additive payload fields are non-breaking by the tolerant-reader rule.

## Open Questions

- None blocking. W3C-PROV export mapping can be designed at dossier time without affecting this schema.
