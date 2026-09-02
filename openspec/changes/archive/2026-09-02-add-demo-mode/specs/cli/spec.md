# cli

## ADDED Requirements

### Requirement: Demo verb

`bokken demo [name]` SHALL create and run a complete dojo session offline —
no API key, no network calls — against a bundled scripted provider and
corpus whose citations resolve, finishing with finalization (dossier, PPTX,
HTML) and printing the report paths plus a zero-cost receipt that states
what a real run typically costs. The output SHALL be deterministic across
runs and machines, and SHALL carry every honesty marker of a real dojo run
(simulated banner, journaled walkthrough skip, requires-real-validation).

#### Scenario: One command to a full report

- **WHEN** `bokken demo` runs on a machine with no ANTHROPIC_API_KEY
- **THEN** it completes with a full journal, resolvable citations, both report files on disk, and a $0.00 receipt printed

#### Scenario: Deterministic showcase

- **WHEN** `bokken demo a` and `bokken demo b` run
- **THEN** their reports differ only in session name and timestamps
