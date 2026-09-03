# handoff

## ADDED Requirements

### Requirement: Executable adapters

`bokken handoff --emit <target>` SHALL render, for each requested target
(`claude-code`, `cursor`, `codex`), a HANDOFF.md execution prompt assembled
without model calls from the canonical package - stating why the work
exists, the execution order, the contradicted-assumption exclusions as
binding, an index of the spec files, explicit relative paths for evidence
lookups (traceability -> dossier.json -> journal.jsonl), and the verbatim
task plan - plus the target-native instruction file (Claude command, Cursor
rules, AGENTS.md). Unknown targets SHALL be refused, and emitting without a
generated package SHALL refuse with a pointer to `bokken handoff`. The
OpenSpec package SHALL remain the single source of truth; adapters carry no
content that contradicts it.

#### Scenario: A coding agent can execute the run's output

- **WHEN** `bokken handoff retention --emit claude-code` runs on a finalized session
- **THEN** `handoff/adapters/claude-code/` holds HANDOFF.md with execution steps, evidence paths, and the task plan, plus `.claude/commands/build-mvp.md`

#### Scenario: Adapters never outrun the package

- **WHEN** `--emit` is requested before the handoff package exists
- **THEN** the command refuses with a pointer to generate the handoff first
