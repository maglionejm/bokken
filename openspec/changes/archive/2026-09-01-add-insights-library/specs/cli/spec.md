# cli

## ADDED Requirements

### Requirement: Library verb

`bokken library [--product KEY]` SHALL list the accumulated learnings
(session, product, verdict, non-untested assumption scores); `--json` SHALL
emit the raw records.

#### Scenario: Learnings from the terminal

- **WHEN** `bokken library --json` runs after a finalized session
- **THEN** stdout is one JSON document containing that session's record
