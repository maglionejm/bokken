# mcp-server Specification

## Purpose
The mcp-server capability exposes Bokken's full session lifecycle to MCP clients — agents and IDEs — as tools and resources over stdio, with the same core, the same JSON contracts as the CLI, and journal-level attribution of agent-driven actions.

## Requirements

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

### Requirement: Actor attribution

Every state-changing operation arriving over MCP SHALL be journaled with
`actor.kind: agent` and the connected client's declared identity (client
name/version from the MCP handshake); gate resolutions and inputs submitted
over MCP SHALL therefore be distinguishable in the ledger from human terminal
actions. Attribution SHALL be applied by the server, not trusted from tool
arguments.

Attribution SHALL extend to answer content, not only to the act of submitting
it: `submit_input` SHALL stamp the handshake actor onto the stored answer, and
the engine that consumes it SHALL journal the resulting evidence with that
actor and confidence class `simulated`. The server SHALL NOT provide any way
for a client to have its answer journaled as human evidence or in a human
confidence class, and SHALL NOT accept a supplied actor for an answer.

#### Scenario: Agent-approved gate is attributed

- **WHEN** a gate is approved via `resolve_gate` from a client identifying as `claude-code`
- **THEN** the `session.gate_resolved` event's actor records kind `agent` and that client identity

#### Scenario: Attribution cannot be spoofed via arguments

- **WHEN** a tool call includes a forged actor field in its arguments
- **THEN** the journaled actor reflects the handshake identity, not the argument

#### Scenario: Submitted answer is not human evidence

- **WHEN** a client answers a pending Founder-mode question via `submit_input` and calls `run_session`
- **THEN** the `evidence.captured` event carries the client's agent actor and confidence class `simulated`, the session's ledger contains no human-attributed record, and decisions resting on that evidence carry `requires_real_validation`

### Requirement: Surface parity

Any behavior reachable through the CLI SHALL be reachable through MCP with equivalent semantics (creation, running, gates, loop-backs, journal, dossier), and both surfaces SHALL share one result-shape contract, so downstream consumers can switch surfaces without remapping.

#### Scenario: Same run, either surface

- **WHEN** an identical offline scripted session is driven once via CLI and once via MCP tools
- **THEN** the resulting journals contain the same event families and payload shapes, differing only in actor attribution

### Requirement: Handoff tool

The server SHALL expose `generate_handoff` returning the package directory, change id, and capability list with the same shapes as the CLI's `--json` contract; refusals (no convergence decision, `kill` recommendation) SHALL surface as tool errors. Completed `run_session` calls SHALL finalize the session exactly as the CLI does (Dossier then handoff, idempotent).

#### Scenario: Agent obtains build-ready specs

- **WHEN** a client calls `run_session` until `completed` and then `generate_handoff`
- **THEN** the handoff package exists and the tool result names the generated capabilities

#### Scenario: Kill recommendation is a tool error

- **WHEN** `generate_handoff` is called for a session whose recommendation is `kill`
- **THEN** the client receives a tool error explaining a killed concept has no build handoff

### Requirement: Client input path confinement

Paths arriving in a tool argument (the `brief.inputs` block of
`create_session`) are untrusted and SHALL be resolved only inside an authorized
input root: the workspace root (`BOKKEN_HOME`, else `./.bokken`) and the working
directory the server was started in. An input path whose resolved real path lies
outside every root — through traversal, a symlink whose target leaves the root,
or an absolute path — SHALL be refused, as SHALL a path that does not exist and
a named file outside the text allowlist. Refusals SHALL surface as tool errors
naming the path and the reason, and no session SHALL be created.

Accepted paths SHALL be journaled in resolved form, and the authorized roots
SHALL be journaled in the immutable session config snapshot so that ingestion
re-checks them when the run actually reads the files. An operator MAY widen the
roots explicitly with `BOKKEN_INPUT_ROOTS` (`os.pathsep`-separated), which
replaces the defaults; a run SHALL never widen its own roots. Operator-supplied
paths on the CLI surface SHALL remain unconfined.

#### Scenario: Named file outside the text allowlist is refused

- **WHEN** `create_session` declares `inputs.documents` naming a suffix-less file such as `id_rsa`
- **THEN** the client receives a tool error naming the allowlist, no session exists, and the file is never read

#### Scenario: Traversal out of the root is refused

- **WHEN** `create_session` declares an input path containing `../` that resolves outside the authorized roots
- **THEN** the client receives a tool error naming the roots and no session is created

#### Scenario: Escaping symlink is refused

- **WHEN** a declared input inside the root is a symlink whose target lies outside it
- **THEN** creation is refused, and a symlink swapped in after creation is skipped by the run rather than read

#### Scenario: Operator widens the roots deliberately

- **WHEN** the operator starts the server with `BOKKEN_INPUT_ROOTS` naming a research directory and a client declares an input inside it
- **THEN** the session is created, the resolved path is journaled in the brief, and the authorized roots appear in the config snapshot
