# Tasks: add-mcp-server

## 1. Contract and server skeleton

- [x] 1.1 Extract the shared result-shape contract into `src/bokken/contract.py` and refit the CLI presenter to consume it; verify existing CLI `--json` tests still pass unchanged
- [x] 1.2 Implement the FastMCP server skeleton with stdio transport, workspace resolution, clientInfo capture, and clean shutdown in `src/bokken/mcp/server.py`; register `bokken serve` in the CLI; verify capability listing and clean-disconnect scenarios with the MCP test client

## 2. Tools

- [x] 2.1 Implement session tools (`create_session`, `run_session`, `step_session`, `stop_session`, `get_status`, `list_sessions`) as thread-offloaded core calls returning contract shapes; verify the Dojo create→run→gate_pending scenario and duplicate-name tool error
- [x] 2.2 Implement interaction tools (`resolve_gate`, `request_loopback`, `submit_input` with pending-question validation); verify programmatic gate approval and stale-input refusal
- [x] 2.3 Implement `query_journal` and `generate_dossier`; verify journal parity with `bokken journal --json` on identical filters

## 3. Resources and attribution

- [x] 3.1 Implement the four resource templates (sessions list, status, filtered journal, dossier); verify dossier resource serves the latest export
- [x] 3.2 Implement server-side actor attribution (handshake identity, spoof-proof against arguments) on all state-changing calls; verify both attribution scenarios in journaled events

## 4. Integration

- [x] 4.1 Surface-parity end-to-end test: drive the identical offline scripted session via CLI and via MCP client; verify equal event families/payload shapes modulo actor, and `make check` green
- [x] 4.2 Document client setup (Claude Code `mcp add` stdio config) in `docs/mcp.md`; verify by connecting a real client to `bokken serve` manually
