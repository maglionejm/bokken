# Proposal: fix-fusion-truncation

## Why

Live r6 defect: 9 of 12 sidekick retrievals hit max_tokens and the
truncated status fell back to the full 834K-token corpus, erasing most of
the projected saving ($101.68 instead of ~$26); separately, the enriched
handoff package outgrew its 16K output cap, and the resulting generation
error aborted finalization (no report). Both are restorations of specified
behavior (delegated retrieval; finalization resilience); no spec deltas.

## What Changes

- Truncated retrievals return their partial verbatim spans (still valid),
  never the full corpus; retrieval headroom raised to 8K tokens.
- Handoff generation streams with a 48K output cap; a generation failure is
  journaled as a skipped-handoff reason and the report still exports
  (`bokken handoff` retries on demand).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none - defect fixes; skip_specs)

## Impact

persona_gen, handoff generate/finalize, regression test.
