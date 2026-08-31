# Orchestrator — spec delta (loop-back rework)

## MODIFIED Requirements

### Requirement: Stage state machine

A session SHALL always be in exactly one stage: `intake`, `empathize`, `define`, `ideate`, `prototype`, `test`, or `complete`. Forward transitions SHALL follow that order. Loop-back transitions SHALL be permitted from `test` to `define` or `empathize`, and from `define` to `empathize`. Every transition SHALL be recorded as a `transition.fired` journal event carrying the firing condition and `refs` to the evidence or decision events that justified it; no transition may occur without such an event. A loop-back means rework: after a loop-back transition, the target stage's engine SHALL run at least once — even when the stage's exit criteria are already satisfied — before exit criteria may move the session forward again, with the rework signal derived from the ledger (no substantive events since the loop-back transition).

#### Scenario: Forward transition records its justification

- **WHEN** `define` completes with a selected problem statement
- **THEN** a `transition.fired` event `define → ideate` is journaled with `refs` including the `decision.recorded` event for the problem statement

#### Scenario: Illegal transition is refused

- **WHEN** a transition `empathize → prototype` is requested
- **THEN** the orchestrator refuses it, no transition event is written, and the session stage is unchanged

#### Scenario: Loop-back is first-class

- **WHEN** a test outcome contradicts a Define-stage insight and the loop-back is accepted
- **THEN** a `transition.fired` event `test → define` is journaled whose `refs` include the contradicting test evidence, and the session re-enters `define` with prior journal history intact

#### Scenario: Loop-back forces rework

- **WHEN** a session loops back to `empathize` although Empathize's exit criteria are already satisfied by prior work
- **THEN** the next run invokes the Empathize engine at least once before any forward transition fires, and its new events are journaled alongside the prior history
