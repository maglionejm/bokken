# Proposal: add-spec-handoff

## Why

The run must not end at the Dossier. The Dossier explains what was learned; the natural next step of the loop is to hand the *validated concept* to whoever builds it. Bokken therefore generates OpenSpec specifications for the concept's MVP — a spec-driven build kickoff derived from the journal (problem statement, winning concept, assumption register with test scores) — ready to be ingested by a different harness component (a coding agent working in the target repository with the OpenSpec workflow). This closes Blueprint §3.2's promise ("prototype: production scaffolding for developers") in spec form: test with wood here, hand over the steel drawings.

## What Changes

- Introduce the handoff generator: derive an OpenSpec-format change package for the validated concept from the session journal, via one journaled model call.
  - Package layout: `handoff/README.md` (ingestion instructions), `handoff/traceability.json` (requirement → ledger event ids), and `handoff/openspec/changes/build-mvp-<slug>/{proposal.md, design.md, specs/<capability>/spec.md, tasks.md}` in strict OpenSpec format.
  - Honesty carry-over: contradicted assumptions become explicit exclusions in design.md (never requirements); untested and `requires_real_validation` items become mandatory validation tasks in tasks.md.
  - Refusal: no handoff without a convergence decision, and none when the test recommendation is `kill`.
- Introduce run finalization: when a run reaches `complete`, the surfaces automatically generate the Dossier and then the handoff (skipping whichever already exists).
- Surface verbs: `bokken handoff <name>` on the CLI and a `generate_handoff` MCP tool.

## Capabilities

### New Capabilities

- `handoff`: OpenSpec MVP-specification generation from a completed run — package contract, format compliance, honesty rules, refusals, and finalization behavior.

### Modified Capabilities

- `cli`: ADDED requirement — `handoff` verb and automatic run finalization (Dossier then handoff on completion).
- `mcp-server`: ADDED requirement — `generate_handoff` tool with the same contract and finalization on completed `run_session`.

## Impact

- New code: `src/bokken/handoff/` (model build, spec generation via ModelRouter, renderers, format validator, finalization helper).
- Modified: CLI `run`/new verb; MCP `run_session`/new tool; fake provider gains a `handoff/specify` handler.
- Depends on: `dossier` (reuses the journal-derived model), `models` (routed generation), `journal` (artifact events).
