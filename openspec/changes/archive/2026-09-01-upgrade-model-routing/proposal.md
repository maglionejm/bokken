# Proposal: upgrade-model-routing

## Why

Live-run output quality on the vatios engagement was judged poor. The founder
directed a model upgrade by agent role: research and challenge agents should
run on Claude Fable 5 at high effort (the deepest reasoning available), while
documentation and execution agents run on Claude Opus 4.8 at high effort.
Today every reasoning call shares one `cognition` class on Opus.

## What Changes

- Routing classes split by agent role: new `research` (interview programs,
  persona turns, follow-ups, outcome derivation) and `challenge` (skeptic,
  convergence lenses, test evaluation and recommendation) classes route to
  `claude-fable-5` with `effort: high` and a server-side refusal fallback to
  `claude-opus-4-8`; `cognition` (stage execution mechanics) and `generation`
  (documentation/artifacts, handoff specs) route to `claude-opus-4-8` with
  adaptive thinking and `effort: high`; `extraction` stays on
  `claude-haiku-4-5`.
- Provider builds Fable 5 requests per its API contract: no `thinking`
  parameter, `output_config.effort`, `betas: ["server-side-fallback-2026-06-01"]`
  with `fallbacks: [{"model": "claude-opus-4-8"}]`, refusal stop reason
  already mapped to the journaled `refused` status.
- Allowlist gains `claude-fable-5`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: routing classes requirement rewritten for the five-class table.

## Impact

`src/bokken/journal/schema.py` (RoutingClass), `src/bokken/models/{router,
anthropic_provider}.py`, call-site class names in `src/bokken/stages/*.py`
and `src/bokken/handoff/generate.py`, `src/bokken/report/context.py` pricing
table, tests.
