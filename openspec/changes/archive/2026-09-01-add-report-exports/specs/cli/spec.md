# cli

## ADDED Requirements

### Requirement: Export verb

`bokken export <name>` SHALL regenerate both report files via the core and
print their paths; `--json` SHALL print a JSON object with both paths. It
SHALL exit `2` when the session does not exist or has no events to report.

#### Scenario: Export from the terminal

- **WHEN** `bokken export mars-lander --json` is invoked on a completed
  session
- **THEN** stdout is one JSON document with the `pptx` and `html` paths and
  the exit code is 0
