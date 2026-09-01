# Proposal: hardening-and-config

## Why

The full v0.7.0 code review surfaced one critical, three high, and several
medium findings plus seven hardcoded tuning parameters; founder mode was
silently excluded from the functional UI testing.

## What Changes

- Founder parity: walkthrough + per-feature UI tests run in both modes when
  `app_url` is declared (spec delta); Ulwick ranking documented dojo-only.
- Cache-marker injection neutralized at render time; zero-segments casting
  guard; `budget_exhausted` journaled as its own status; `verify_chain()` on
  every writer open; handoff fails loudly on out-of-range assumption
  indexes; assumption score_refs accumulate evidence; MCP mailbox writes are
  rename-atomic.
- Config knobs with unchanged defaults: ideation.novelty_window,
  empathize.opportunity_bands/segment_spike, walkthrough.max_pages,
  ui_tests.max_features/max_steps.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize walkthrough mode parity.

## Impact

prompts/provider, casting, router+journal schema, store, replay, handoff
render, mcp mailbox, stage config reads, docs.
