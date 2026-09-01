# mcp-server

## MODIFIED Requirements

### Requirement: Journal and dossier access

The server SHALL expose `query_journal` (same filters as the CLI: type/family, stage, actor, since, limit) returning JSONL-equivalent structured events, `generate_dossier` returning both export paths and status, `export_report` returning the PPTX and HTML report paths, and `cost_report` returning the per-stage/prompt/class cost rows with totals and cache hit rate (same shapes as the CLI `--json` contracts). It SHALL also expose read resources: `bokken://sessions` (list), `bokken://sessions/{name}/status`, `bokken://sessions/{name}/journal` (the full ledger as JSONL; filtered access goes through the `query_journal` tool), and `bokken://sessions/{name}/dossier` (latest generated `dossier.json` content).

#### Scenario: Journal query parity with CLI

- **WHEN** the same filter is issued via `query_journal` and via `bokken journal --json`
- **THEN** both return the same events in the same canonical form

#### Scenario: Dossier resource serves the latest export

- **WHEN** a dossier has been generated and the dossier resource is read
- **THEN** the returned content is the current `dossier.json` for that session

#### Scenario: Reports and costs over MCP

- **WHEN** a client calls `export_report` and `cost_report` on a completed session
- **THEN** it receives the same paths and cost totals the CLI verbs emit
