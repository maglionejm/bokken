# mcp-server

## ADDED Requirements

### Requirement: Desktop bundle

The project SHALL ship a Claude Desktop MCP Bundle built from a checked-in
manifest that wraps `uvx bokken==<released-version> serve` - configuration
only, never vendored code - declaring every registered tool, a sensitive
optional API-key field (the demo requires none), and workspace/input-root
directories. The build SHALL inject the package version, and a test SHALL
fail when the manifest's declared tools differ from the server's registered
tools.

#### Scenario: One-click install cannot drift

- **WHEN** a tool is added to or removed from the MCP server without updating the manifest
- **THEN** the test suite fails on the manifest/server tool-set comparison

#### Scenario: The bundle pins the release

- **WHEN** `make mcpb` runs on a released commit
- **THEN** the packed manifest's version and its `uvx bokken==X serve` pin both equal the package version
