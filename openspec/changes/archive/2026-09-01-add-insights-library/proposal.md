# Proposal: add-insights-library

## Why

Every run starts from zero: r6 re-discovered what r4 had already scored.
The research-repository market (Dovetail) is built on the opposite premise:
research compounds across studies into organizational memory.

## What Changes

- New `library` capability: workspace-level learnings JSONL appended at
  finalization; prior-learnings digest seeds the interview program of new
  runs on the same product, with session provenance; `bokken library` verb.

## Capabilities

### New Capabilities

- `library`: cross-run learnings with provenance.

### Modified Capabilities

- `cli`: library verb.

## Impact

src/bokken/library.py (new), finalize hook, interview_program v4, CLI,
tests.
