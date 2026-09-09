# Change: fix-demo-resume-offline

## Why

Review C, finding 1 (honesty): a `bokken demo` session interrupted and
resumed via `bokken run` wired the REAL provider (`cli/wiring.py
build_runner` used `provider_router_factory` unconditionally) while
`bokken costs` and the deck kept claiming "$0.00 charged" because
`config.demo` is true. One resume with a key in the environment and the
receipt is a lie; without a key the resume refuses instead of continuing
the offline demo.

## What Changes

- `cli/wiring.py` grows `session_router_factory(session_dir)`: it reads
  `session_config(session_dir).get("demo")` and returns a
  DemoProvider-backed router factory for demo sessions, falling through to
  the module-level `router_factory()` (the seam tests patch) otherwise.
- `build_runner` and every session-scoped finalize path — the `run` verb's
  `finalize_session`, the `handoff` verb, and the MCP server's `_runner`,
  `run_session` finalization, and `generate_handoff` tool — wire through
  `session_router_factory`, so a resumed demo stays offline and $0.00
  stays true over both surfaces.

## Impact

- Affected specs: `cli` (MODIFIED: Demo verb — demo sessions stay offline
  across resumes)
- Affected code: `cli/wiring.py`, `cli/app.py` (run finalize + handoff),
  `mcp/server.py` (runner construction, run finalization, handoff tool)
