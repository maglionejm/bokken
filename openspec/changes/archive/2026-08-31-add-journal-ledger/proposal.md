# Proposal: add-journal-ledger

## Why

Bokken's defining output property is explaining the process, not just the result (Blueprint §5). The Journal — an event-sourced, append-only process ledger — is the moat: every artifact must be traceable to the evidence, the utterance, and the reasoning that produced it, including paths not taken. It is also the crash-safety mechanism: session state is a fold over the ledger, which is what makes barista-style pause/resume of named sessions possible. Every other MVP capability (orchestrator, panel, stages, dossier, CLI, MCP) writes to or reads from it, so it must land first and its schema must be designed first (Blueprint §7.1: "This is the moat; design the schema first").

## What Changes

- Introduce the versioned Journal event schema v1: a common envelope plus ten event families (session, evidence, interpretation, option, decision, assumption, facilitation, transition, model, artifact).
- Introduce append-only JSONL storage per session with a tamper-evident hash chain, atomic appends, and durable writes.
- Introduce replay: folding a journal into a typed `SessionState` (current stage, open questions, assumption register, idea lineage, decision log, budgets).
- Introduce the session workspace layout on disk and session addressing by name.
- Introduce a query interface over the ledger (filter by type/stage/actor, follow mode) used later by the CLI, MCP, and Dossier generator.

## Capabilities

### New Capabilities

- `journal`: the event-sourced process ledger — event taxonomy and envelope, append-only storage, hash chain, replay to session state, and ledger queries.

### Modified Capabilities

(none — greenfield)

## Impact

- New code: `src/bokken/journal/` (schema, store, replay, query).
- New dependency use: pydantic v2 for event models (already in pyproject).
- Downstream: every other MVP change depends on this schema; changes to it after freeze require a spec delta with a migration note (see CONTRIBUTING.md).
