# cli

## ADDED Requirements

### Requirement: Validate verb

`bokken validate <name> [--participant NAME] [--channel terminal]` SHALL
build (or reuse) the validation guide and run one agentic interview over the
selected channel, journaling exchanges and rescoring; `--guide-only` SHALL
stop after producing the guide. Exit code 2 when the session has no research
debt and no untested assumptions.

#### Scenario: Guide only

- **WHEN** `bokken validate mars-lander --guide-only` runs on a completed session
- **THEN** a `validation_guide` artifact exists and no interview is started
