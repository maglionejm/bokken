# Proposal: add-mcp-report-tools

## Why

The CLI grew `export` and `costs` verbs; surface parity requires the MCP
server to expose the same capabilities with the same contracts.

## What Changes

- New MCP tools `export_report` and `cost_report` mirroring the CLI verbs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `mcp-server`: journal/dossier access requirement gains both tools.

## Impact

`src/bokken/mcp/server.py`, MCP tests, docs/mcp.md.
