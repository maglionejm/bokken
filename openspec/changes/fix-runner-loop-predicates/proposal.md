# Proposal: fix-runner-loop-predicates

## Why

`Runner._loop` carried its correctness predicates inline, where they were too
small to notice and too embedded to test. Two of them failed open, and both
were live on `main` (reproduced against the pre-change runner):

1. **An unrecognized gate policy disabled every gate, silently.**
   `_gate_required` ended in `return from_stage in policy`, so any value that
   was not one of the two recognized literals fell through to a membership
   test. A singular typo — `stage_boundary` for `stage_boundaries` — made that
   test false at every stage, and a dojo run went `intake -> complete`
   requesting **zero** gates with no warning. A raw string degraded further
   into substring matching. Gates are the mechanism that keeps an autonomous
   run under human control (Blueprint §4, constitution non-negotiable 4), so
   failing open here is a governance failure, not a config nit.

2. **Rework after a loop-back was discharged by any event at all.**
   `_rework_pending` was true only while `state.events_since_transition == 0`,
   and replay increments that counter for every non-`session.*` record —
   including the router's own `model.called` telemetry. So when a human looped
   the run back to `empathize` because a segment went unheard and the engine's
   model call was then refused, the refusal record alone satisfied the rework
   check: the loop fast-forwarded on exactly the evidence the human looped back
   to replace, and the intervention became a no-op. The orchestrator spec
   already asked for "no substantive events since the loop-back transition";
   the counter did not implement "substantive".

## What Changes

- The loop's decisions become named, individually testable functions in
  `runner.py`: `normalize_gate_policy`, `resolve_gate_policy`,
  `gate_required`, `default_gate_policy`, `is_substantive_work`,
  `rework_pending`, `halt_result`, `approved_gate_target`, `stall_detail`, and
  a `_stop_on_budget` method. `_loop` now reads as the sequence of decisions it
  is. The state machine itself is untouched: forward progress is still derived
  from exit criteria and only loop-backs are engine-proposed.
- A gate policy is validated instead of interpreted. The legal forms are
  `none`, `stage_boundaries`, and a list of stages that have a forward exit;
  anything else raises `GatePolicyError` (an `OrchestratorError`, so the CLI's
  existing refusal contract gives exit code 2 and the MCP surface a
  `ToolError`, with no change needed at either boundary). Creation refuses
  before the session directory exists — including a policy arriving through
  `config_extra` — and every `run` re-validates from the journal before any
  work is done or any token spent.
- A journal that declares no gate policy resolves it the way creation does,
  from the mode, so an absent declaration can no longer read as "no gates" for
  an autonomous run.
- Rework after a loop-back requires substantive work by the target stage's
  engine: a record in the evidence (input rejections excluded — they are
  grounding gaps), interpretation, option, decision, assumption, or artifact
  families, or an executed facilitation move, appended after the loop-back and
  stamped with the target stage. Bookkeeping and telemetry no longer count. A
  stage that cannot produce rework now fails loudly through the existing stall
  guard, with a message that says the loop-back is unaddressed.
- Redundant journal replays are removed: the loop reads and folds the journal
  once per iteration and re-uses that snapshot for its predicates, and the
  post-engine stall check no longer re-reads a journal it knows is unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `orchestrator`: an unrecognized gate policy is refused rather than
  interpreted, and the loop-back rework signal requires substantive work by
  the target stage rather than any appended record.

## Impact

`src/bokken/orchestrator/runner.py` and `tests/orchestrator/`. No journal
schema change and no migration: existing journals replay identically, and a
journal carrying an illegal gate policy is refused rather than mis-read.
Behavior changes visible to operators: a misspelled `--gates` value now fails
with exit code 2 instead of producing a gateless run (already covered by the
CLI spec's "invalid usage or refused operation" exit code, so no `cli` delta),
and a loop-back whose engine does no substantive work now stalls loudly
instead of fast-forwarding. `GatePolicyError` is not yet re-exported from
`bokken.orchestrator`'s `__all__`; that is a one-line follow-up outside this
change's file lane and is not needed for the refusal contract, which keys on
`OrchestratorError`.
