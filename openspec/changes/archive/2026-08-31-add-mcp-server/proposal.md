# Proposal: add-mcp-server

## Why

Bokken must be consumable by other agents, not only humans at a terminal (user requirement: "terminal, or even MCP"; Blueprint §7.1 names MCP as the tool surface). An MCP server makes every Bokken session drivable from Claude Code, IDEs, and any MCP client — the Dojo becomes a tool an orchestrating agent can call, with the Journal keeping the same audit guarantees regardless of who is driving.

## What Changes

- Introduce `bokken serve`: an MCP server (stdio transport) over the same core the CLI uses.
- Introduce MCP tools mirroring the CLI verbs: `create_session`, `run_session`, `step_session`, `stop_session`, `get_status`, `list_sessions`, `resolve_gate`, `request_loopback`, `submit_input` (answer a pending Founder-mode question programmatically), `query_journal`, `generate_dossier`.
- Introduce MCP resources for read access: session status, journal (with filters via templated URIs), and dossier documents.
- Introduce actor attribution: operations arriving over MCP are journaled with `actor.kind: agent` and the client identity, so ledgers distinguish human-driven from agent-driven actions.

## Capabilities

### New Capabilities

- `mcp-server`: the MCP surface — server lifecycle, tool contract, resource contract, and actor attribution.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/mcp/` plus the `serve` verb registered in the CLI app.
- New dependency use: official `mcp` Python SDK (already declared).
- Depends on: all core capabilities; shares result shapes with the CLI's `--json` contract (one contract, two surfaces).
