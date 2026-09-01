# Proposal: add-fusion-lanes

## Why

r5 cost $120.55 with $101.62 in interview turns carrying the full corpus
and a 0% cache hit rate. The Devin Fusion architecture — a frontier lane
plus a cost-effective sidekick lane, each with persistent parallel caches,
delegation of mechanical reads, judgment kept on the frontier — is the
founder-mandated golden rule for the fix.

## What Changes

- New `sidekick` routing class → `claude-opus-5`: delegated corpus
  retrieval for interview turns (source-marked spans, threshold-gated) and
  mechanical UI-step selection with frontier-confirmed verdicts.
- Prompt cache split marker; provider sends the prefix as a
  cache-controlled block (parallel per-lane caches).
- Default total-token budget at `bokken new` (honest stop, no cost
  surprises).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: sidekick class, parallel caches, judgment-stays-frontier.

## Impact

router/provider/prompts, persona_gen, ui_tests, CLI default budget, tests.
