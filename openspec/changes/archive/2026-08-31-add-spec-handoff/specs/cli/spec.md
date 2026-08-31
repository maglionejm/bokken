# CLI — spec delta (handoff)

## ADDED Requirements

### Requirement: Handoff verb and run finalization

The CLI SHALL provide `bokken handoff <name>` generating the OpenSpec handoff package via the core and printing the package directory (with `--json` returning the directory, the change id, and the capability list). When `bokken run` halts `completed`, the CLI SHALL finalize the session automatically — Dossier first, then handoff — skipping outputs that already exist and skipping the handoff for `kill` recommendations, reporting in the run output what was generated or skipped.

#### Scenario: Handoff from the terminal

- **WHEN** `bokken handoff mars-lander --json` runs on a completed session with a `proceed` recommendation
- **THEN** stdout is a single JSON document with the package path and generated capabilities, and the package exists on disk

#### Scenario: Completion finalizes automatically

- **WHEN** `bokken run mars-lander` returns `completed` for the first time
- **THEN** the Dossier and the handoff package are generated without further commands, and a second `run` does not regenerate them
