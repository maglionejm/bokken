# Design: add-dt-orchestrator

## Context

See proposal.md. Constraints: the journal is the only state store (add-journal-ledger); the loop must be identical across Founder/Dojo; no workflow-framework dependency (CLAUDE.md non-negotiable 5). Stage *content* (what happens inside empathize/define/…) is deliberately out of scope here — stage engines arrive in add-stage-engines and plug into slots this change defines.

## Goals / Non-Goals

**Goals:**

- A small, explicit, testable state machine whose every effect is a journal event.
- A `StageEngine` protocol (slot) that add-stage-engines implements, so orchestration lands and is testable before any LLM code exists.
- Gates/budgets/stopping enforced in code, not prompts (Blueprint §8: "intervention budgets enforced in code, not prompt").

**Non-Goals:**

- Stage cognition, persona panels, model calls (later changes).
- Parallel stage execution or multi-session scheduling.

## Decisions

1. **Hand-rolled state machine as data + pure functions** — a `TRANSITIONS` table (frozen dict of allowed edges with condition kinds) and `can_exit(stage, state) -> CriteriaVerdict`. Alternatives: `transitions` library or LangGraph — rejected: the table is ~7 edges; a dependency would obscure the product logic.
2. **`StageEngine` protocol** — `run(ctx: StageContext) -> StageOutcome` where `StageContext` exposes replayed state, a journal appender, the Kata, and an input port; `StageOutcome` declares proposed transition or loop-back. The orchestrator, not engines, writes `transition.fired` — engines cannot move the machine directly.
3. **Input port abstraction** — `InputPort.ask(prompt, kind) -> answer` implemented by the terminal (Founder) or the panel (Dojo). This is the single seam where modes differ, satisfying the mode-agnostic core requirement.
4. **Gates as journal-visible halts** — a pending gate is just derived state (`gate_requested` without matching `gate_resolved`); `run` exits cleanly when one is pending. Gate resolution is an ordinary append (from CLI/MCP), so approval works across processes.
5. **Kata triggers as plain predicates over `SessionState`** — registry entries are dataclass-like pydantic models with a `trigger: Callable[[SessionState], TriggerFire | None]`. LLM-assisted trigger detection (e.g. "problem statement is solution-shaped") is exposed as a `Judge` seam injected later by model-ops; the registry itself stays deterministic and unit-testable with fakes.
6. **Budget accounting from replay** — token budgets and move budgets are counters in `SessionState` folded from `model.called` / `facilitation.move_executed` events. No side ledger.

## Risks / Trade-offs

- [Exit criteria too rigid for real briefs] → criteria are declared per stage in one module with explicit override recorded as a gate approval ("proceed despite unmet criterion X" is a journaled human decision).
- [Kata triggers that need semantic judgment can't be pure predicates] → the `Judge` seam defers those to model-ops; until then such moves trigger only on structural signals (counts, rates, flags).
- [State machine and stage engines developed in different changes drift] → the `StageEngine` protocol + a `FakeStageEngine` used by orchestrator tests is the contract; stage engines must pass the same protocol test suite.

## Open Questions

- None blocking.
