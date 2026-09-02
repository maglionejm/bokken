# Proposal: confine-client-input-paths

## Why

`create_session_tool` accepts a fully client-controlled `brief`, and its
`inputs` block flowed into corpus ingestion with no root confinement, no
allowlist for explicitly named files, and no size cap. A remote MCP caller could
therefore declare `documents: ["/home/victim/.ssh/id_rsa"]` (the suffix filter
only applied to directory walks) or name a home directory and have its text
files walked recursively; ingested corpus text is rendered into persona prompts,
so this read arbitrary server files into an outbound request body. That is
silent self-escalation: a run reaching resources the operator never authorized
(Blueprint §5, constitution non-negotiable 4).

The CLI is not the same surface. A human naming a path on their own machine is
the operator exercising their own authority, and must keep working unchanged, so
the confinement belongs at the agent-facing boundary rather than in the core.

## What Changes

- Confine client-supplied `brief.inputs` paths at the MCP surface to an
  authorized input root (the workspace root and the server's working
  directory), refusing traversal, escaping symlinks, outside absolute paths, and
  missing paths as clean tool errors before any session is created.
- Journal the authorized roots in the session config snapshot and re-check them
  during ingestion, so a symlink swapped in after creation is skipped, not read.
- Give the operator one explicit way to widen the reach: `BOKKEN_INPUT_ROOTS`.
- For every caller, apply the text-suffix allowlist to explicitly named files
  (not only to directory walks) and cap ingestion per file and per ingested set.
- Journal a refused or skipped declared input as `evidence.input_rejected`
  instead of dropping it silently; CLI-created sessions declare no roots and
  keep resolving operator paths as before.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `mcp-server`: client-supplied input paths are confined and refusals surface as
  tool errors.
- `panel`: ingestion narrows to the allowlist and size caps for named files too,
  and honors journaled input roots.
- `journal`: taxonomy v1 gains `evidence.input_rejected`.

## Impact

`src/bokken/panel/corpus.py`, `src/bokken/mcp/server.py`,
`src/bokken/journal/schema.py`, `src/bokken/stages/{base,empathize,ideate}.py`,
`docs/mcp.md`, `docs/operating.md`, `docs/events.md`, and tests under
`tests/panel/`, `tests/mcp/`, `tests/cli/`.
