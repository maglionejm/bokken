# Proposal: add-cli-surface

## Why

The MVP is consumed through the terminal (Founder mode's solo workspace, Blueprint §3.2/§11) in the barista.sh style: a named, durable, resumable session driven by lifecycle verbs. The CLI is the first surface over the shared core — it must expose the whole loop (create, run, step, gates, loop-backs, journal, dossier) without adding any logic of its own, so the same core stays byte-identical under MCP.

## What Changes

- Introduce the `bokken` CLI (Typer + Rich) with session-lifecycle verbs:
  - `bokken new <name>` — create a session (interactive brief intake or `--brief <file>`), with mode, gate policy, budgets, corpus, and routing options.
  - `bokken run <name>` — continue the loop from replayed state (interactive in Founder mode; `--dojo` sessions run headless to the next gate/stop).
  - `bokken step <name>` — advance at most one stage.
  - `bokken status <name>` / `bokken list` — session state, pending gates, budgets.
  - `bokken gate <name> approve|reject [--reason]` — resolve pending gates.
  - `bokken back <name> <stage> --reason` — human-initiated loop-back.
  - `bokken journal <name>` — query/tail the ledger with filters.
  - `bokken dossier <name>` — generate and locate the dossier.
  - `bokken stop <name>` — stop a run (journaled human stop).
- Introduce output discipline: human-readable Rich output by default, `--json` for machine-readable output on every read command, plain utilitarian English, no emojis, documented exit codes.

## Capabilities

### New Capabilities

- `cli`: the terminal surface — verbs, interaction contract, output modes, and exit codes.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/cli/` (entry point `bokken.cli.app:main`, already declared in pyproject).
- Depends on: all prior capabilities (thin adapter only — no business logic in the CLI).
