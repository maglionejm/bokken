# Proposal: route-execution-to-opus-5

## Why

Claude Opus 5 (`claude-opus-5`, adaptive thinking, effort high, 1M context)
is now documented and matches the founder's original routing intent for
execution and documentation work, which had been mis-routed to Fable 5 when
the model was believed not to exist.

## What Changes

- `cognition` and `generation` default to `claude-opus-5` (adaptive, effort
  high); research/challenge stay on `claude-fable-5`; allowlist gains
  `claude-opus-5` and `claude-sonnet-5`; price table updated.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: routing classes defaults.

## Impact

router, provider tests, price table, docs.
