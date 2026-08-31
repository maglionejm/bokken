# Tasks: add-spec-handoff

## 1. Generation core

- [x] 1.1 Implement the `SpecPackage` structured-output schema and the `handoff/specify` prompt in `src/bokken/handoff/`; verify schema round-trip with the fake provider handler
- [x] 1.2 Implement renderers (proposal/design/specs/tasks/README/traceability) with normalization (SHALL, kebab-case, scenario scaffolds) and the structural format validator gating writes; verify with unit tests for each normalization and the never-half-written rule
- [x] 1.3 Implement honesty carry-over in code: contradicted assumptions stripped from requirements and listed as design exclusions with refs; untested + requires_real_validation become mandatory validation tasks; Dojo README banner; verify each with targeted fixtures
- [x] 1.4 Implement refusals (no convergence decision; `kill` recommendation) writing nothing; verify both

## 2. Finalization and surfaces

- [x] 2.1 Implement `bokken.handoff.finalize` (dossier then handoff, idempotent via journal artifact kinds) and wire it into CLI `run` and MCP `run_session` on `completed`; verify completion-produces-both and idempotence scenarios
- [x] 2.2 Add `bokken handoff <name>` (with `--json`) and the `generate_handoff` MCP tool sharing contract shapes; verify CLI scenario and MCP kill-refusal tool error

## 3. Integration

- [x] 3.1 End-to-end offline: completed Dojo session → finalize → package exists, traceability resolves against the ledger, format assertions pass, `make check` green
