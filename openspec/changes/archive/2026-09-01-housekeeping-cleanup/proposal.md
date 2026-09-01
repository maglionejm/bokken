# Proposal: housekeeping-cleanup

## Why

Founder-requested file-by-file cleanup and simplification after the v0.6.x
feature run. A repo-wide scan found two dead artifacts and three duplicated
patterns; behavior is unchanged (skip_specs).

## What Changes

- Dead code removed: unused `Provocation` schema and the never-invoked
  `ideate/provoke` prompt.
- Shared helpers `short_id()` and `content_hash()` in the journal schema
  replace eight duplicated hashlib call sites (casting, corpus, mcp,
  ui_tests, research, empathize, walkthrough, report).
- Agent demarcation: evidence nodes carry the journaled actor name, so the
  concept-researcher, ui-walker, and ui-tester appear by name in stage
  digests, report pipeline cards, and the deck roster.
- Docs: routing-override note clarified in operating.md.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none - cleanup/refactor; skip_specs)

## Impact

schemas/prompts (deletions), journal schema (helpers), eight call sites,
dossier model + report renderers (agent names), operating.md.
