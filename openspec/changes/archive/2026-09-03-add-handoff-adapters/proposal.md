# Change: add-handoff-adapters

## Why

Issue #48: the handoff ends at a directory of specs that assumes the consumer
already knows OpenSpec, and its README pointed at evidence without paths.
Making the run's output directly executable by the user's coding agent
completes the wooden-sword-to-steel loop.

## What Changes

- `bokken handoff --emit claude-code|cursor|codex` (repeatable) renders thin
  adapters under `handoff/adapters/<target>/`: an executable HANDOFF.md
  (why, execution order, binding exclusions, spec index, evidence-lookup
  paths, verbatim task plan) plus the target-native file (.claude command,
  .cursor rules, AGENTS.md). No model calls; the OpenSpec package stays
  canonical.
- The handoff README now gives explicit relative paths to dossier.json and
  journal.jsonl and explains how to resolve assumption ids to evidence.

## Impact

- Affected specs: `handoff` (ADDED requirement)
- Affected code: `handoff/emit.py` (new), `handoff/render.py` README block,
  `cli/app.py`, `contract.HandoffResult.adapters`
