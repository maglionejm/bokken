# MCP server — spec delta (handoff)

## ADDED Requirements

### Requirement: Handoff tool

The server SHALL expose `generate_handoff` returning the package directory, change id, and capability list with the same shapes as the CLI's `--json` contract; refusals (no convergence decision, `kill` recommendation) SHALL surface as tool errors. Completed `run_session` calls SHALL finalize the session exactly as the CLI does (Dossier then handoff, idempotent).

#### Scenario: Agent obtains build-ready specs

- **WHEN** a client calls `run_session` until `completed` and then `generate_handoff`
- **THEN** the handoff package exists and the tool result names the generated capabilities

#### Scenario: Kill recommendation is a tool error

- **WHEN** `generate_handoff` is called for a session whose recommendation is `kill`
- **THEN** the client receives a tool error explaining a killed concept has no build handoff
