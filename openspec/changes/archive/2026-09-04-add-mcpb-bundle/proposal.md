# Change: add-mcpb-bundle

## Why

Claude Desktop installs local MCP servers natively via one-click MCP Bundles
(.mcpb). Bokken's config-file install works but is not native; the bundle
removes the last friction for the largest desktop audience.

## What Changes

- `mcpb/manifest.json` template: wraps `uvx bokken==<version> serve` (the
  bundle carries configuration, never code), user_config for the API key
  (sensitive, optional - the demo needs none), workspace, and input roots;
  declares all 14 tools.
- `make mcpb` builds `dist/bokken-<version>.mcpb` with the released version
  injected; the bundle attaches to each GitHub release.
- Drift guard: a test asserts the manifest's declared tools equal the
  server's registered tools, and that the packed version matches the
  package version.

## Impact

- Affected specs: `mcp-server` (ADDED requirement)
- Affected code: `mcpb/manifest.json`, `scripts/build_mcpb.py`, `Makefile`,
  docs
