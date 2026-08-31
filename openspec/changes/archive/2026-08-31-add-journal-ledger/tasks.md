# Tasks: add-journal-ledger

## 1. Schema

- [x] 1.1 Implement the envelope model and the nine event families as pydantic v2 discriminated unions in `src/bokken/journal/schema.py`; verify with unit tests that valid events round-trip and each malformed-envelope case from the spec is rejected
- [x] 1.2 Implement confidence classes and the simulated-provenance invariant (persona evidence cannot be `observed`); verify with a test that constructing such an event raises
- [x] 1.3 Implement canonical serialization + SHA-256 record hashing with genesis constant; verify with a property test (serialize → hash → parse → re-hash equality over generated events)

## 2. Store

- [x] 2.1 Implement `JournalStore` (append with seq assignment, fsync, hash chaining; iterate; verify_chain) over per-session `journal.jsonl`; verify with tests for contiguous seq, byte-identical read-back, and first-broken-link detection on tampered bytes
- [x] 2.2 Implement session workspace resolution (`./.bokken/sessions/<slug>/`, `BOKKEN_HOME` override), create/list/resolve-by-name, duplicate-name refusal; verify with tmp-dir tests
- [x] 2.3 Implement single-writer locking via `flock`; verify with a test spawning a second opener that fails fast
- [x] 2.4 Crash-safety test: kill a writer subprocess mid-append loop and verify every line parses, seq is contiguous, and the chain verifies

## 3. Replay and queries

- [x] 3.1 Implement `SessionState` and the pure fold in `src/bokken/journal/replay.py` covering stage, brief/mode, gates, evidence index, insights with grounding, idea lineage, assumption register, decision log with dissent, budgets, stop status; verify with fixture journals per stage
- [x] 3.2 Verify replay determinism (same file → equal states) and resume semantics (state after stop mid-ideate matches pre-stop state) with tests
- [x] 3.3 Implement query API (type/family, stage, actor, seq/time range) and follow mode; verify with tests including a live-append follower

## 4. Integration

- [x] 4.1 Export a minimal public API (`bokken.journal`: schema, store, replay, query) and document it in module docstrings; verify `make check` passes end-to-end
