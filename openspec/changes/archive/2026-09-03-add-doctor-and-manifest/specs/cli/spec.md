# cli

## ADDED Requirements

### Requirement: Doctor verb

`bokken doctor` SHALL report, offline by default, the environment facts a
run depends on - version, workspace path and writability, provider key
presence (values never printed), each optional extra with the consequence
of its absence, browser availability when the ui extra is present, Twilio
credential completeness when the interview extra is present, and the MCP
input-root configuration - pairing every failing check with the exact fix
command. `--network` SHALL add provider reachability probes; `--json` SHALL
emit the same checks machine-readably with an overall `ok` flag.

#### Scenario: A failing environment explains itself

- **WHEN** `bokken doctor` runs with no API key and no extras
- **THEN** each missing item shows its consequence and its fix command, and secrets are never echoed

#### Scenario: Machine-readable diagnosis

- **WHEN** `bokken doctor --json` runs
- **THEN** stdout is one JSON document with per-check name/ok/detail/fix and an overall ok flag
