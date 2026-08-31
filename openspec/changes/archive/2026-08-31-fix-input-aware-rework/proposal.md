# Proposal: fix-input-aware-rework

## Why

The first live Dojo run (against the vatios repository) surfaced two defects. (1) The Empathize interview program was generated blind to the declared inputs: with a code/docs corpus and no discussion transcripts, every behavioral question correctly abstained, Define had zero grounded evidence, and the stall guard aborted the run. (2) Looping back to a stage whose exit criteria are already satisfied was a no-op: the criteria-first runner fast-forwarded without ever re-running the engine, making rework impossible.

## What Changes

- Empathize calibrates its interview program to the input kinds actually declared (corpus-answerable questions for code/metrics/docs; behavioral laddering when discussions exist; at most one explicitly-flagged human-research question per segment). Prompt `empathize/interview_program` bumped to v2.
- After a loop-back transition, the target stage's engine SHALL run at least once before exit criteria may fast-forward the session (rework semantics), derived from the ledger (`events_since_transition`).
- Dossier: when a stage recorded several decisions across engine attempts, Part A now cites the latest, not the first.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `orchestrator`: loop-back transitions gain rework semantics (MODIFIED Stage state machine requirement).
- `stages`: the Empathize engine's interview program becomes input-aware (MODIFIED Empathize engine requirement).

## Impact

- Code: `src/bokken/models/prompts.py`, `src/bokken/stages/empathize.py`, `src/bokken/orchestrator/runner.py`, `src/bokken/journal/replay.py` (fold counter), `src/bokken/dossier/model.py`.
- Tests: rework end-to-end test; prompt-version assertion loosened.
