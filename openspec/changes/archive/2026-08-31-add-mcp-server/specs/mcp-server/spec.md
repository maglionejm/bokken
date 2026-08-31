# MCP server — spec delta

## Purpose

The mcp-server capability exposes Bokken's full session lifecycle to MCP clients — agents and IDEs — as tools and resources over stdio, with the same core, the same JSON contracts as the CLI, and journal-level attribution of agent-driven actions.

## ADDED Requirements

### Requirement: Server lifecycle

`bokken serve` SHALL start an MCP server on stdio that exposes the tools and resources below for the workspace it is started in (honoring `BOKKEN_HOME`). The server SHALL run multiple sequential operations across sessions without restart, and SHALL shut down cleanly on client disconnect leaving all sessions resumable.

#### Scenario: Client connects and lists capabilities

- **WHEN** an MCP client connects to `bokken serve`
- **THEN** the tool list contains all tools in this spec with JSON-schema'd inputs and descriptions, and the resource templates are advertised

#### Scenario: Disconnect leaves sessions clean

- **WHEN** the client disconnects while a session sits at a pending gate
- **THEN** the server exits without corrupting the journal, and the session is resumable from the CLI

### Requirement: Session tools

The server SHALL expose tools mirroring the CLI lifecycle with identical result shapes to the CLI's `--json` contract: `create_session` (name, brief content or path, mode, gates, budgets, corpus paths, routing overrides), `run_session` (advance to next halt; returns halt kind and state), `step_session`, `stop_session`, `get_status`, and `list_sessions`. Tool errors SHALL be returned as MCP tool errors with the same categories as CLI exit codes (invalid/refused vs unexpected), never as protocol failures.

#### Scenario: Agent creates and runs a Dojo session

- **WHEN** a client calls `create_session` (mode `dojo`) then `run_session`
- **THEN** the run advances to the first gate and the result reports halt kind `gate_pending` with the same shape as `bokken status --json`

#### Scenario: Refused operation is a tool error

- **WHEN** `create_session` is called with an existing name
- **THEN** the client receives a tool error naming the conflict, and no session state changes

### Requirement: Interaction tools

The server SHALL expose `resolve_gate` (approve/reject with mandatory reason on reject), `request_loopback` (target stage + reason, validated against legal edges), and `submit_input` (answer the session's pending input question by id). `submit_input` SHALL fail if the referenced question is not currently pending.

#### Scenario: Programmatic gate approval

- **WHEN** `resolve_gate` approves a pending gate and `run_session` is called
- **THEN** the resolution event is journaled and the run proceeds past the boundary

#### Scenario: Stale input is refused

- **WHEN** `submit_input` references a question already answered
- **THEN** the tool returns an error and no event is journaled

### Requirement: Journal and dossier access

The server SHALL expose `query_journal` (same filters as the CLI: type/family, stage, actor, since, limit) returning JSONL-equivalent structured events, and `generate_dossier` returning both export paths and status. It SHALL also expose read resources: `bokken://sessions` (list), `bokken://sessions/{name}/status`, `bokken://sessions/{name}/journal` (the full ledger as JSONL; filtered access goes through the `query_journal` tool), and `bokken://sessions/{name}/dossier` (latest generated `dossier.json` content).

#### Scenario: Journal query parity with CLI

- **WHEN** the same filter is issued via `query_journal` and via `bokken journal --json`
- **THEN** both return the same events in the same canonical form

#### Scenario: Dossier resource serves the latest export

- **WHEN** a dossier has been generated and the dossier resource is read
- **THEN** the returned content is the current `dossier.json` for that session

### Requirement: Actor attribution

Every state-changing operation arriving over MCP SHALL be journaled with `actor.kind: agent` and the connected client's declared identity (client name/version from the MCP handshake); gate resolutions and inputs submitted over MCP SHALL therefore be distinguishable in the ledger from human terminal actions. Attribution SHALL be applied by the server, not trusted from tool arguments.

#### Scenario: Agent-approved gate is attributed

- **WHEN** a gate is approved via `resolve_gate` from a client identifying as `claude-code`
- **THEN** the `session.gate_resolved` event's actor records kind `agent` and that client identity

#### Scenario: Attribution cannot be spoofed via arguments

- **WHEN** a tool call includes a forged actor field in its arguments
- **THEN** the journaled actor reflects the handshake identity, not the argument

### Requirement: Surface parity

Any behavior reachable through the CLI SHALL be reachable through MCP with equivalent semantics (creation, running, gates, loop-backs, journal, dossier), and both surfaces SHALL share one result-shape contract, so downstream consumers can switch surfaces without remapping.

#### Scenario: Same run, either surface

- **WHEN** an identical offline scripted session is driven once via CLI and once via MCP tools
- **THEN** the resulting journals contain the same event families and payload shapes, differing only in actor attribution
