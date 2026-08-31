# CLI — spec delta

## Purpose

The CLI is Bokken's terminal surface: barista-style lifecycle verbs over named, durable, resumable sessions, exposing the full DT loop — creation, running, gates, loop-backs, ledger, and dossier — as a thin adapter over the shared core with disciplined human and machine output.

## ADDED Requirements

### Requirement: Session lifecycle verbs

The CLI SHALL provide: `bokken new <name>` (create; interactive brief intake by default, `--brief <file>` for non-interactive; options for `--mode founder|dojo`, `--gates`, `--budget`, typed inputs — `--repo <path>` for an app repository to explore, `--metrics <path>` for business/performance data, `--discussion <path>` for interview transcripts and needs statements, `--doc <path>` for other documents (each repeatable) — and routing overrides), `bokken run <name>` (resume-and-continue; halts at pending gate, pending human input, stop, or completion), `bokken step <name>` (at most one stage), `bokken stop <name>`, `bokken status <name>`, and `bokken list`. All verbs SHALL address sessions by name and operate purely through the core (no CLI-side state).

#### Scenario: New then run then interrupt then run

- **WHEN** a user creates `mars-lander`, runs it, kills the process mid-stage, and runs it again
- **THEN** the second run resumes from the journal without repeated work and without any CLI-side recovery steps

#### Scenario: Non-interactive creation

- **WHEN** `bokken new mars-lander --brief brief.md --mode dojo` is invoked with a valid brief file
- **THEN** the session is created without prompting, and `bokken status mars-lander` reports stage `intake`, mode `dojo`, and the default Dojo gate policy

#### Scenario: Status shows what blocks progress

- **WHEN** a Dojo run has halted at a gate
- **THEN** `bokken status` names the pending gate, the stage boundary it guards, and the command to resolve it

### Requirement: Gate and loop-back verbs

The CLI SHALL provide `bokken gate <name> approve|reject [--reason <text>]` resolving the pending gate (rejection requires a reason) and `bokken back <name> <stage> --reason <text>` requesting a human-initiated loop-back to a legal earlier stage. Both SHALL act by appending the corresponding journal events through the core; illegal targets (no pending gate; illegal loop-back edge) SHALL fail with a specific error and exit code 2.

#### Scenario: Approve resumes the run

- **WHEN** `bokken gate mars-lander approve` is invoked with a gate pending and then `bokken run mars-lander`
- **THEN** the gate resolution is journaled and the run proceeds past the boundary

#### Scenario: Illegal loop-back is refused

- **WHEN** `bokken back mars-lander prototype` is invoked from stage `define`
- **THEN** the command fails with exit code 2 naming the legal loop-back edges

### Requirement: Journal access

`bokken journal <name>` SHALL print ledger events with filters `--type <type-or-family>`, `--stage <stage>`, `--actor <kind>`, `--since <seq|timestamp>`, `--limit <n>`, and `--follow` (stream new events until interrupted). Default output SHALL be a compact human-readable line per event; `--json` SHALL emit one canonical JSON event per line (JSONL).

#### Scenario: Filtered tail

- **WHEN** `bokken journal mars-lander --type option --stage ideate --follow` runs during divergence
- **THEN** only `option.*` events from `ideate` stream, one per line, as they are appended

### Requirement: Dossier verb

`bokken dossier <name>` SHALL generate the dossier via the core and print the paths of `dossier.md` and `dossier.json`; `--json` SHALL print a JSON object with the paths and dossier status (`complete|partial`). Generation for in-flight sessions SHALL be permitted and labeled partial per the dossier capability.

#### Scenario: Dossier from the terminal

- **WHEN** `bokken dossier mars-lander --json` is invoked mid-run
- **THEN** the output JSON contains both file paths and `"status": "partial"`

### Requirement: Founder-mode interaction contract

During interactive runs the CLI SHALL render stage openings, questions, syntheses, and Kata move outputs as plain conversational prompts; user answers SHALL be captured through the core's input port (journaled as human evidence/decisions per the schema). Interactive prompts SHALL always display which stage the session is in and SHALL support saving-and-exiting cleanly (Ctrl-C leaves the session resumable, never corrupt).

#### Scenario: Ctrl-C is safe

- **WHEN** the user interrupts an interactive interview mid-question
- **THEN** the process exits cleanly, no partial event is written, and `bokken run` resumes at the pending question

### Requirement: Output discipline and exit codes

All output SHALL be plain utilitarian English without emojis or decorative Unicode. Every read verb SHALL support `--json` emitting stable, documented shapes. Exit codes SHALL be: `0` success (including clean halts at gates/stops), `1` unexpected error, `2` invalid usage or refused operation (unknown session, illegal transition, validation failure). Errors SHALL be written to stderr; machine output to stdout only.

#### Scenario: Machine consumption is clean

- **WHEN** `bokken status mars-lander --json` succeeds
- **THEN** stdout contains exactly one JSON document, stderr is empty, and the exit code is 0

#### Scenario: Unknown session

- **WHEN** any verb references a session name that does not exist
- **THEN** the command exits 2 with a stderr message naming the workspace searched
