# Tasks: fix-demo-resume-offline

## 1. Implementation

- [x] 1.1 `session_router_factory(session_dir)` in cli/wiring.py selects the
  DemoProvider-backed router when the journaled session config carries
  `demo: true`; `build_runner`, the run verb's finalize, the handoff verb,
  and the MCP server's three wiring sites consume it; regression test
  resumes a stopped demo via `bokken run` with no provider keys and asserts
  DemoProvider wiring, completion, and the $0.00 costs label
