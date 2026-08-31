# Design: fix-input-aware-rework

## Context

See proposal.md - two live-run defects.

## Goals / Non-Goals

**Goals:** rework semantics derived from the ledger (no side state); interview calibration via prompt, enforcement stays with grounding/abstention.

**Non-Goals:** retrieval/scoping changes; new event types.

## Decisions

1. Rework signal = last transition is a loop-back AND zero non-`session.*` events since (fold counter `events_since_transition`), so `session.resumed` noise cannot mask pending rework.
2. Input calibration lives in the prompt (v2) + an `inputs_available` summary computed from the brief - personas' grounding/abstention still enforces honesty in code.

## Risks / Trade-offs

- [Engines may loop again on other empty-corpus shapes] -> the stall guard bounds any such case at 4 attempts with a clear error.
