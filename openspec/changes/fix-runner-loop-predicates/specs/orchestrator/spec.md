# orchestrator Specification Delta

## MODIFIED Requirements

### Requirement: Stage state machine

A session SHALL always be in exactly one stage: `intake`, `empathize`, `define`, `ideate`, `prototype`, `test`, or `complete`. Forward transitions SHALL follow that order. Loop-back transitions SHALL be permitted from `test` to `define` or `empathize`, and from `define` to `empathize`. Every transition SHALL be recorded as a `transition.fired` journal event carrying the firing condition and `refs` to the evidence or decision events that justified it; no transition may occur without such an event.

A loop-back means rework: after a loop-back transition, the target stage's engine SHALL do substantive work — even when the stage's exit criteria are already satisfied — before exit criteria may move the session forward again. The rework signal SHALL be derived from the ledger, and "substantive" SHALL be decided by record type, not by record count: rework stays outstanding until the journal holds, after the loop-back transition and stamped with the target stage, a record of work in the evidence (an input rejection excepted — it records a grounding gap), interpretation, option, decision, assumption, or artifact families, or an executed facilitation move. Bookkeeping and telemetry SHALL NOT discharge it: `session.*` records, `transition.fired`, a suppressed facilitation move, and `model.called` — whatever its status, since a refused, errored, or even successful call is not itself a contribution — SHALL leave the rework outstanding. A target stage whose engine cannot produce substantive rework SHALL fail loudly under the stall guard, naming the loop-back as unaddressed, rather than fast-forward on the pre-loop-back ledger.

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

#### Scenario: A refused model call does not discharge rework

- **WHEN** a human loops the session back to `empathize` and the only record the engine appends is a `model.called` event with `status: refused`
- **THEN** no forward transition fires, the session stays in `empathize`, and the run ends by reporting the stalled stage instead of completing on the evidence the loop-back was meant to replace

### Requirement: Human gates

Gate policy SHALL be configurable per session at creation, and its only recognized forms SHALL be `none`, `stage_boundaries` (a gate before every forward transition), and an explicit list of stages that have a forward exit to gate. Dojo-mode sessions SHALL default to `stage_boundaries`.

Any other value SHALL be refused with an error that names the legal forms: a misspelled literal, a comma-joined string, a list naming anything that is not a gateable stage, or a value of another type. An unrecognized policy SHALL NEVER be interpreted as "no gates", and SHALL NEVER degrade into a membership or substring test. The refusal SHALL happen at session creation before anything is journaled — whatever route the policy arrived by — and again at the start of every run, before the run does any work or spends any token. A session whose journal declares no gate policy at all SHALL resolve one the way creation does, from the mode, and never to `none` for an autonomous run.

When a gate is reached the orchestrator SHALL journal `session.gate_requested`, halt, and expose the pending gate in session state. The run SHALL only continue after a `session.gate_resolved` event; a rejection SHALL keep the session in the current stage with the rejection reason journaled. An approval SHALL only fire the transition it guards: an approval for a stage the session has since left SHALL fire nothing.

#### Scenario: Dojo run pauses at a gate

- **WHEN** a Dojo session with default gate policy finishes `define`
- **THEN** the run halts with a pending gate visible in status, and no `ideate` work occurs until the gate is approved

#### Scenario: Gate rejection keeps the stage

- **WHEN** a pending gate is rejected with a reason
- **THEN** `session.gate_resolved` records the rejection and reason, and the session remains in the current stage for rework

#### Scenario: A misspelled gate policy is refused, not silently obeyed

- **WHEN** a session is created or run with the gate policy `stage_boundary`
- **THEN** the operation fails with an error naming the legal forms (exit code 2 at the CLI), nothing is journaled, and no stage of that session ever runs ungated

#### Scenario: An undeclared policy is not a gateless run

- **WHEN** a Dojo session's journaled config names no gate policy at all
- **THEN** the run resolves the mode default and halts for approval at its first forward transition
