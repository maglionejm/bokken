# Tasks: add-dt-orchestrator

## 1. State machine

- [x] 1.1 Implement stages, the `TRANSITIONS` table (forward edges + loop-backs), and transition validation in `src/bokken/orchestrator/machine.py`; verify with tests that legal edges pass, `empathize → prototype` is refused, and every accepted transition emits `transition.fired` with refs
- [x] 1.2 Implement per-stage entry/exit criteria evaluated over replayed `SessionState`; verify with fixture states that each spec criterion blocks/permits as specified and that verdicts name the unmet criterion

## 2. Session runner

- [x] 2.1 Implement `create` (brief validation → `session.created`), `run`, `step`, `stop` in `src/bokken/orchestrator/runner.py` against the `StageEngine` protocol with a `FakeStageEngine`; verify with tests for step-semantics and clean run-to-completion
- [x] 2.2 Implement resumability: `run` replays then continues, journaling `session.resumed`; verify with a test that kills a fake-engine run mid-stage and resumes without re-execution
- [x] 2.3 Implement the `InputPort` seam with a terminal stub and a scripted test double; verify Founder-mode pending-input halts and resumes

## 3. Gates, budgets, stopping

- [x] 3.1 Implement gate policies (`none` / `stage_boundaries` / stage list; Dojo default `stage_boundaries`), pending-gate derivation, approve/reject via journal append; verify with tests for halt-at-gate, cross-process approval (separate store handle), and rejection-keeps-stage
- [x] 3.2 Implement budget counters (tokens per routing class, novelty floor hook) and stopping rules emitting `session.stopped` with enumerated reasons; verify with tests for budget exhaustion mid-stage and reason auditability
- [x] 3.3 Implement the no-silent-self-escalation guard (brief/budget/gate immutability in Dojo runs + journaled refusal); verify with a test attempting each forbidden mutation

## 4. Kata

- [x] 4.1 Implement the move registry model (id, intent, stages, trigger, params schema, surfaces, budget) and the nine MVP moves with structural triggers in `src/bokken/kata/`; verify registry introspection lists all moves with complete metadata
- [x] 4.2 Implement execute/suppress flow writing `facilitation.move_executed` / `facilitation.move_suppressed` with reasons; verify with tests for out-of-stage suppression, budget-exhausted suppression, and budget-survives-resume
- [x] 4.3 Implement the `Judge` seam (protocol only, fake in tests) for semantic triggers; verify moves depending on it stay inert without a judge
- [x] 4.4 Implement tone-contract rendering helpers (depersonalized critique templates, devil's-advocate labeling); verify with snapshot tests of rendered move outputs

## 5. Integration

- [x] 5.1 End-to-end test: fake engines + real journal drive a session `intake → complete` in both modes with gates on; verify identical event-family shape across modes and `make check` green
