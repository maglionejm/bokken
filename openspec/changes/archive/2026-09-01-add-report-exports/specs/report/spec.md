# report

## ADDED Requirements

### Requirement: Deterministic journal-only generation

Report generation SHALL be a deterministic function of the Journal and of
files already exported to the session directory. It SHALL make no model
calls, and regenerating SHALL produce identical content up to timestamps.

#### Scenario: No model calls during export

- **WHEN** `export` runs on a completed session
- **THEN** the count of `model.called` events is unchanged afterwards

### Requirement: Two formats, journaled

Export SHALL write `report/report.pptx` (a PowerPoint deck) and
`report/report.html` (a self-contained HTML page telling the same story) in
the session directory, and journal each as `artifact.generated` with kinds
`report_deck` and `report_page` and content hashes. Export SHALL be
idempotent: files are overwritten, but a session that already journaled both
kinds is not re-journaled by finalization.

#### Scenario: Both files exist and are journaled

- **WHEN** export completes
- **THEN** both files exist and `artifact.generated` events with kinds
  `report_deck` and `report_page` are in the Journal

### Requirement: Full process coverage

Both formats SHALL report the entire process and its intermediate outputs —
the brief and inputs, the stage arc including loop-backs, evidence samples
with confidence classes, problem-statement candidates with losers and why
they lost, the concept decision with dissent, prototype artifacts with
assumption mappings, the scored assumption register, facilitation moves, and
research debt — and the final outputs: the recommendation, validation flags,
dossier and handoff pointers, and model usage with an estimated cost labeled
as a list-price estimate.

#### Scenario: Intermediate outputs are present

- **WHEN** a completed dojo session is exported
- **THEN** the HTML contains the problem statement, at least one losing
  option with its `why_lost`, every assumption with its score, and the
  recommendation

### Requirement: Spec appendix

The report SHALL end with an appendix listing each generated handoff spec as
exactly one sentence (taken from the spec's own Purpose text, never
re-generated) followed by the relative path to the full spec file. When the
handoff was refused, the appendix SHALL state the refusal reason instead.

#### Scenario: Specs summarized with pointers

- **WHEN** a session with a generated handoff package is exported
- **THEN** the appendix lists every capability spec with a one-sentence
  summary and its `handoff/openspec/changes/...` path

#### Scenario: Refusal is surfaced

- **WHEN** a killed session is exported
- **THEN** the appendix states that the handoff was refused and why

### Requirement: Honesty carry-over

For dojo sessions both formats SHALL carry the simulated-run banner on the
cover/summary, the synthetic share of the evidence base, and the
requires-real-validation flag on the recommendation.

#### Scenario: Banner survives both formats

- **WHEN** a dojo session is exported
- **THEN** both the deck cover and the HTML header state the run is
  simulated and requires validation with real users
