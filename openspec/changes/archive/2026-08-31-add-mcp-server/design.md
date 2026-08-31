# Design: add-mcp-server

## Context

See proposal.md. Constraints: one result-shape contract shared with the CLI (`--json` shapes); the core is synchronous while the MCP SDK is asyncio; attribution must come from the handshake, not tool arguments.

## Goals / Non-Goals

**Goals:**

- FastMCP-based server that is a *pure adapter*: every tool body is core call + shared presenter, nothing else.
- Long-running `run_session` calls that behave well over MCP (halt-based semantics keep individual calls bounded: run-to-next-halt, not run-to-completion).

**Non-Goals:**

- HTTP/SSE transport, auth, multi-tenant serving (stdio + local workspace only for MVP).
- Sampling/elicitation back to the client (the `submit_input` tool covers programmatic answers; interactive elicitation via MCP is a future change).
- Push notifications of journal events (clients poll `query_journal` with `since`).

## Decisions

1. **Official `mcp` SDK, FastMCP server, stdio transport** — the standard, lightest path; tools declared with typed signatures generate JSON schemas automatically.
2. **Async boundary via `anyio.to_thread`** — the synchronous core runs in worker threads from async tool handlers; the journal's single-writer lock already serializes session mutations, and the server additionally serializes state-changing calls per session to avoid lock-contention errors surfacing to clients.
3. **Shared contract module** — `src/bokken/contract.py` (typed result models used by both CLI presenter and MCP tool returns). Any shape change is a spec-level event for both surfaces.
4. **Halt-based `run_session`** — returns at the next gate/input/stop/completion exactly like `bokken run`, so no tool call is unbounded; orchestrating agents loop: `run → resolve_gate/submit_input → run`.
5. **Attribution injected server-side** — the server captures `clientInfo` at initialization and stamps every core call's actor context; tool schemas expose no actor field.

## Risks / Trade-offs

- [Long Dojo stages still make single `run_session` calls slow] → acceptable for MVP (MCP clients handle long tools); if needed later, add a `step_session`-based fine-grained loop — already specified.
- [Contract drift between surfaces] → the shared contract module plus the parity end-to-end test make drift a test failure, not a discovery by users.

## Open Questions

- None blocking.
