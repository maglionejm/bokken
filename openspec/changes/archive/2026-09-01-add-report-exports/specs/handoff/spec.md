# handoff

## MODIFIED Requirements

### Requirement: Run finalization

When a run reaches `complete`, the system SHALL finalize it: generate the
Dossier, then the handoff package, then the report exports automatically (in
that order), skipping any output that already exists (finalization is
idempotent), and skipping the handoff — with the reason journal-visible in
the run result — when the recommendation is `kill`. Report exports SHALL be
generated even when the handoff is skipped.

#### Scenario: Completion produces both outputs

- **WHEN** a run halts `completed` on a session with a `proceed` or
  `iterate` recommendation and no prior exports
- **THEN** the Dossier, the handoff package, and both report files exist
  afterwards without further commands

#### Scenario: Killed runs still get a report

- **WHEN** a run halts `completed` with a `kill` recommendation
- **THEN** the handoff is skipped with the reason recorded, and both report
  files exist with the refusal surfaced in the appendix

#### Scenario: Finalization is idempotent

- **WHEN** `run` is invoked again on an already-finalized session
- **THEN** no duplicate dossier, handoff, or report generation occurs
