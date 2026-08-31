# Handoff — spec delta

## Purpose

The handoff capability turns a completed run's validated concept into build-ready OpenSpec specifications: a change package derived from the journal — problem statement, winning concept, assumption register with test scores — that a different harness component (a coding agent using the OpenSpec workflow) can ingest and implement, with the run's honesty guarantees carried into the specs.

## ADDED Requirements

### Requirement: Handoff package generation

Given a session with a journaled convergence decision, the system SHALL generate a handoff package in the session workspace under `handoff/`: `README.md` (what the package is and how to ingest it into a target repository), `traceability.json` (mapping every generated capability and requirement to the ledger event ids it derives from: the problem-statement decision, the concept decision, and assumption ids), and `openspec/changes/build-mvp-<session-slug>/` containing `proposal.md`, `design.md`, at least one `specs/<capability>/spec.md`, and `tasks.md`. Spec content generation SHALL go through the model router (journaled `model.called`), and every written file SHALL be journaled as `artifact.generated` with its content hash.

#### Scenario: Completed run yields an ingestable package

- **WHEN** handoff generation runs on a completed session whose recommendation is `proceed` or `iterate`
- **THEN** the package exists with proposal, design, at least one capability spec, tasks, README, and traceability, and every file has an `artifact.generated` event

#### Scenario: Traceability resolves to the ledger

- **WHEN** `traceability.json` is read
- **THEN** every referenced event id exists in the session journal, including the concept decision and every assumption carried into requirements or tasks

### Requirement: OpenSpec format compliance

Generated spec files SHALL comply with the OpenSpec change format so they validate strictly in a target repository: each capability spec starts with a `## Purpose` section of at least 50 characters followed by `## ADDED Requirements`; every requirement is a `### Requirement:` header whose text uses SHALL; every requirement has at least one `#### Scenario:` with `- **WHEN**` / `- **THEN**` lines; capability directory names are kebab-case; `tasks.md` uses numbered `## n.` groups of `- [ ] n.m` checkboxes each stating its verification; `proposal.md` lists every generated capability under `### New Capabilities`. The system SHALL verify these rules structurally before writing and SHALL fail generation (writing nothing) if the generated content cannot be made compliant.

#### Scenario: Structural validation gates the export

- **WHEN** the model produces a requirement without a scenario or a statement without SHALL
- **THEN** the generator repairs it deterministically (normative phrasing, scenario scaffold) or fails without writing files — a non-compliant package is never written

#### Scenario: Package validates in a target repo

- **WHEN** the generated change directory is copied into a repository initialized with OpenSpec
- **THEN** `openspec validate --strict` passes for the change

### Requirement: Honesty carry-over

The handoff SHALL preserve the run's epistemic state: assumptions scored `contradicted` SHALL NOT appear as requirements and SHALL be listed in `design.md` as explicit exclusions with their ledger refs; assumptions scored `untested` and any decision flagged `requires_real_validation` SHALL produce mandatory validation tasks in `tasks.md`; and the package README SHALL state, for Dojo runs, that the concept was validated against a synthetic panel and which items await real-user validation.

#### Scenario: Contradicted assumption becomes an exclusion

- **WHEN** the register contains a contradicted assumption
- **THEN** no requirement embodies it, and design.md lists it as an exclusion citing the contradicting evidence ids

#### Scenario: Simulated validation debt becomes tasks

- **WHEN** the test recommendation carries `requires_real_validation`
- **THEN** tasks.md contains explicit real-user validation tasks that cannot be satisfied by more simulation

### Requirement: Refusals

Handoff generation SHALL refuse — with a specific error and nothing written — when the session has no journaled convergence decision, or when the test recommendation is `kill`.

#### Scenario: Killed concept is not specified

- **WHEN** handoff is requested for a session whose recommendation is `kill`
- **THEN** generation refuses, explaining that a killed concept has no build handoff, and no files or artifact events are produced

### Requirement: Run finalization

When a run reaches `complete`, the system SHALL finalize it: generate the Dossier and then the handoff package automatically (in that order), skipping any output that already exists (finalization is idempotent), and skipping the handoff — with the reason journal-visible in the run result — when the recommendation is `kill`.

#### Scenario: Completion produces both outputs

- **WHEN** a run halts `completed` on a session with a `proceed` or `iterate` recommendation and no prior exports
- **THEN** the Dossier and the handoff package both exist afterwards without further commands

#### Scenario: Finalization is idempotent

- **WHEN** `run` is invoked again on an already-finalized session
- **THEN** no duplicate dossier or handoff generation occurs
