# Proposal: add-dt-orchestrator

## Why

The DT loop is the product logic (Blueprint §7.1: "own this code"). Bokken models Design Thinking as an explicit state machine — five stages plus intake and completion, with first-class loop-back transitions — so a run is a governed process rather than a prompt chain (Blueprint §3.4). The Kata (Blueprint §4.2) makes facilitation itself auditable: every intervention is a named, parameterized, budgeted move logged like a tool call. Together they are the shared core both Founder mode and the Dojo execute on.

## What Changes

- Introduce the stage state machine (`intake → empathize → define → ideate → prototype → test → complete`) with entry/exit criteria, loop-back transitions, and journal-recorded firing conditions.
- Introduce the session runner: create (brief intake), run (continue from replayed state), step (single stage), stop; resumability comes from journal replay.
- Introduce human gates: configurable checkpoints at stage boundaries (mandatory in Dojo runs by default) that pause the run pending approve/reject.
- Introduce the Kata move registry with the MVP move set, triggers, budgets, and mandatory execution/suppression logging.
- Introduce run budgets and stopping rules (token budget, novelty floor, criteria satisfaction, human stop) enforced by the orchestrator — never "the answer looked good".

## Capabilities

### New Capabilities

- `orchestrator`: the DT stage state machine, session lifecycle, loop-backs, gates, budgets, and stopping rules.
- `kata`: the facilitation move library — named, parameterized, budgeted moves with triggers and full audit logging.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/orchestrator/`, `src/bokken/kata/`.
- Depends on: `journal` (all state is journal-derived; all actions are events).
- Downstream: `stages` engines plug into stage slots; `cli`/`mcp` invoke the runner; `panel` supplies Dojo participants.
