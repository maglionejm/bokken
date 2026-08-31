# Consuming Bokken over MCP

`bokken serve` exposes the full session lifecycle over MCP (stdio): the same core
the CLI uses, with identical JSON result shapes, plus journal-level attribution —
state-changing calls arriving over MCP are journaled with `actor.kind: agent` and
the client's handshake identity.

## Claude Code

```sh
claude mcp add bokken -- uv run --directory /path/to/bokken bokken serve
```

Or with an installed package: `claude mcp add bokken -- bokken serve`.
Set `ANTHROPIC_API_KEY` in the server's environment and start it from the
directory whose `.bokken/` workspace you want (or set `BOKKEN_HOME`).

## Tools

| Tool | Purpose |
| --- | --- |
| `create_session_tool` | Create a session (brief + mode + gates + budgets + typed inputs) |
| `run_session` / `step_session` / `stop_session` | Advance to the next halt / one stage / stop |
| `get_status` / `list_sessions_tool` | Session state and workspace listing |
| `resolve_gate` | Approve or reject the pending gate (reject needs a reason) |
| `request_loopback` | Return to an earlier stage on a legal loop-back edge |
| `submit_input` | Answer a pending Founder-mode question by id, then run again |
| `query_journal` | Filtered ledger reads (type/family, stage, actor, since, limit) |
| `generate_dossier` | Produce `dossier.md` / `dossier.json` and return the paths |
| `generate_handoff` | Produce the OpenSpec MVP-spec package for the validated concept (tool error for killed concepts) |

## Resources

- `bokken://sessions` — session list
- `bokken://sessions/{name}/status` — derived state
- `bokken://sessions/{name}/journal` — the full ledger (JSONL)
- `bokken://sessions/{name}/dossier` — the latest `dossier.json`

## Driving a run

```text
create_session_tool -> run_session -> (gate_pending? resolve_gate)
                                   -> (input_pending? submit_input)
                                   -> run_session ... until halt == completed
```

`run_session` always returns at the next halt, so no call is unbounded. A
completed run is finalized automatically — the result carries
`finalization: dossier generated; handoff specs generated` — after which the
dossier resource serves Part C and the handoff package sits in the session
workspace, ready for ingestion (see `docs/handoff.md`). `generate_dossier` /
`generate_handoff` regenerate on demand.
