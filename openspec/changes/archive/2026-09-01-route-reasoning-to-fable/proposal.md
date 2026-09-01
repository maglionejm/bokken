# Proposal: route-reasoning-to-fable

## Why

The founder reviewed the v0.2.0 live run and does not want Opus-tier
reasoning anywhere: the "Opus 5" originally requested for execution and
documentation does not exist, and the nearest superior tier is Fable 5. All
reasoning classes move to `claude-fable-5` at effort high.

## What Changes

- `cognition` and `generation` default to `claude-fable-5` (effort high,
  server-side refusal fallback to `claude-opus-4-8` — Opus appears only as a
  refusal rescue, never as primary). `extraction` stays on haiku.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: routing classes requirement updated.

## Impact

`src/bokken/models/router.py`, `src/bokken/stages/base.py` (facilitator
actor metadata), tests, docs.
