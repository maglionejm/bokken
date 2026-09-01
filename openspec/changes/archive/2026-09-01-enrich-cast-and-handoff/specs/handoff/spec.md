# handoff

## MODIFIED Requirements

### Requirement: Handoff package generation

Given a session with a journaled convergence decision, the system SHALL generate a handoff package in the session workspace under `handoff/`: `README.md` (what the package is and how to ingest it into a target repository), `traceability.json` (mapping every generated capability and requirement to the ledger event ids it derives from: the problem-statement decision, the concept decision, and assumption ids), and `openspec/changes/build-mvp-<session-slug>/` containing `proposal.md`, `design.md`, at least one `specs/<capability>/spec.md`, and `tasks.md`. Spec content generation SHALL go through the model router (journaled `model.called`), and every written file SHALL be journaled as `artifact.generated` with its content hash. Each capability SHALL carry a slice plan (1-3 slices with S/M/L size and what ships) and its dependencies, and the package SHALL carry a sequencing list - the build order with per-step rationale - rendered into the proposal.

#### Scenario: Completed run yields an ingestable package

- **WHEN** handoff generation runs on a completed session whose recommendation is `proceed` or `iterate`
- **THEN** the package exists with proposal, design, at least one capability spec, tasks, README, and traceability, and every file has an `artifact.generated` event

#### Scenario: Traceability resolves to the ledger

- **WHEN** `traceability.json` is read
- **THEN** every referenced event id exists in the session journal, including the concept decision and every assumption carried into requirements or tasks

#### Scenario: Slices and sequencing reach the proposal

- **WHEN** a handoff package is generated
- **THEN** the proposal contains a slice plan per capability and a numbered sequencing section
