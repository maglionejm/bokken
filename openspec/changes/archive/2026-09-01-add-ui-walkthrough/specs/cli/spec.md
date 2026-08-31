# cli

## MODIFIED Requirements

### Requirement: Session lifecycle verbs

The CLI SHALL provide: `bokken new <name>` (create; interactive brief intake by default, `--brief <file>` for non-interactive; options for `--mode founder|dojo`, `--gates`, `--budget`, typed inputs — `--repo <path>` for an app repository to explore, `--app-url <url>` for a running instance of the product to walk through, `--metrics <path>` for business/performance data, `--discussion <path>` for interview transcripts and needs statements, `--doc <path>` for other documents (each repeatable) — and routing overrides), `bokken run <name>` (resume-and-continue; halts at pending gate, pending human input, stop, or completion), `bokken step <name>` (at most one stage), `bokken stop <name>`, `bokken status <name>`, and `bokken list`. All verbs SHALL address sessions by name and operate purely through the core (no CLI-side state).

#### Scenario: New then run then interrupt then run

- **WHEN** a user creates `mars-lander`, runs it, kills the process mid-stage, and runs it again
- **THEN** the second run resumes from the journal without repeated work and without any CLI-side recovery steps

#### Scenario: Non-interactive creation

- **WHEN** `bokken new mars-lander --brief brief.md --mode dojo` is invoked with a valid brief file
- **THEN** the session is created without prompting, and `bokken status mars-lander` reports stage `intake`, mode `dojo`, and the default Dojo gate policy

#### Scenario: Status shows what blocks progress

- **WHEN** a Dojo run has halted at a gate
- **THEN** `bokken status` names the pending gate, the stage boundary it guards, and the command to resolve it
