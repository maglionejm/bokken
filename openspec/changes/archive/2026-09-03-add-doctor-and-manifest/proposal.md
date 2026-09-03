# Change: add-doctor-and-manifest

## Why

Issue #48: first-run failure modes (missing key, missing extra, missing
browser) are exactly what makes evaluators bounce, and the environment
matrix grew with every extra. MCP registries are the highest-intent
discovery channel and Bokken is invisible there.

## What Changes

- `bokken doctor [--network] [--json]`: one-screen diagnosis - version,
  workspace writability, key presence (never values), each extra with its
  consequence when absent, chromium cache, Twilio credentials, input roots,
  and (opt-in) provider reachability - every failing row paired with the
  exact fix command.
- `server.json` MCP registry manifest at the repo root; install one-liners
  (Claude Code / Claude Desktop) in docs/mcp.md. Registry submission itself
  stays pending owner sign-off (external publication).

## Impact

- Affected specs: `cli` (ADDED requirement)
- Affected code: `cli/doctor.py` (new), `cli/app.py`, `server.json`,
  `docs/mcp.md`
