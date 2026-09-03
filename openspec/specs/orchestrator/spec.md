# orchestrator Specification

## Purpose
The orchestrator is the executable Design Thinking loop: a stage state machine with entry/exit criteria, first-class loop-backs, human gates, budgets, and stopping rules, driving a session from brief intake to a completed, journaled run in either Founder (interactive) or Dojo (autonomous) mode.

## Requirements

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

### Requirement: Stage entry and exit criteria

Each stage SHALL declare entry criteria (what must exist in session state to start) and exit criteria (what must exist to leave forward). The orchestrator SHALL evaluate exit criteria against replayed session state, not against in-memory flags. Minimum exit criteria: `intake` — a brief with problem space, constraints, target segments, success criteria, and risk tolerance; `empathize` — at least one evidence event per target segment or an explicit research-debt abstention; `define` — a selected problem statement recorded as a decision with evidence-linked insights; `ideate` — at least one surviving option with recorded convergence decision; `prototype` — at least one artifact linked to an assumption register; `test` — a scored assumption register and a kill/iterate/proceed recommendation decision.

#### Scenario: Exit blocked until criteria met

- **WHEN** `ideate` is asked to complete while no convergence decision exists in the journal
- **THEN** the orchestrator refuses the forward transition and reports which exit criterion is unmet

#### Scenario: Criteria evaluated from replay

- **WHEN** a resumed session is asked to transition
- **THEN** the criteria evaluation uses only journal-derived state, yielding the same verdict as before the interruption

### Requirement: Session lifecycle and resumability

The orchestrator SHALL support: `create` (validate and journal the brief as `session.created`, entering `intake`), `run` (advance the loop from replayed state until completion, a pending gate, a stopping rule, or — in Founder mode — a pending human input), `step` (run at most one stage then return), and `stop` (journal `session.stopped` with `reason: human_stop`). Any interruption at any point SHALL be resumable: `run` on an existing session first replays the journal and continues; completed work is never re-executed.

#### Scenario: Run resumes after interruption

- **WHEN** a run is killed during `prototype` and `run` is invoked again
- **THEN** the session resumes in `prototype` without repeating completed stages, and a `session.resumed` event is journaled

#### Scenario: Step advances exactly one stage

- **WHEN** `step` is invoked on a session in `define`
- **THEN** the session runs at most through the end of `define` and control returns, leaving the session in `define` (exit pending) or `ideate`

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

### Requirement: Budgets and stopping rules

A session SHALL carry budgets from the brief: a total token budget (with per-routing-class sub-budgets) and, for Dojo ideation, a novelty floor. The orchestrator SHALL stop the run — journaling `session.stopped` with the specific reason — when the token budget is exhausted, the novelty rate falls below the floor during divergence, the brief's success criteria are met, or a human stops the run. Runs SHALL never terminate merely because output "looked good"; the stopping reason is always one of the enumerated causes, recorded as a ledger event.

#### Scenario: Budget exhaustion stops the run

- **WHEN** cumulative journaled token usage reaches the session budget mid-`ideate`
- **THEN** the run halts, `session.stopped` records `reason: budget_exhausted`, and the session remains resumable after the budget is raised

#### Scenario: Stopping reason is auditable

- **WHEN** any Dojo run terminates
- **THEN** the journal's final events include exactly one `session.stopped` whose `reason` is one of the enumerated causes

### Requirement: No silent self-escalation

An autonomous (Dojo) run SHALL NOT expand its own brief, alter its budgets, gate policy, or success criteria, contact real humans, or publish outputs anywhere outside the session workspace. Any attempt SHALL be refused and journaled as a suppressed action.

#### Scenario: Brief expansion is refused

- **WHEN** any component in a Dojo run attempts to widen the brief's problem space or raise its own token budget
- **THEN** the orchestrator refuses, the attempt is journaled, and the original brief remains in force

### Requirement: Mode-agnostic core

Founder mode and Dojo mode SHALL execute the same state machine, criteria, gates, budgets, and journal schema; they SHALL differ only in who supplies participation — the human at the terminal (Founder) or the synthetic panel (Dojo) — so that any run is auditable through the identical ledger regardless of mode.

#### Scenario: Identical journals across modes

- **WHEN** a Founder run and a Dojo run each complete the same stages
- **THEN** both journals validate against the same schema and contain the same event families for the loop mechanics (transitions, decisions, facilitation, model calls), differing only in actor provenance and confidence classes

### Requirement: Input provenance

The input-port seam SHALL carry the provenance of whoever supplied an answer,
not only the answer text. `InputPort.ask` SHALL return an answer object
carrying the text and the `Actor` that supplied it; that actor SHALL be
mandatory, so no port can hand a stage engine an unattributed answer. The
terminal port SHALL report a human actor (the person typing at the prompt); any
port that brokers answers from elsewhere SHALL report the actor it received
them from — for the MCP input mailbox, the submitting client's handshake
identity. Ports SHALL NOT accept a supplier identity from the answer content or
from a caller's arguments.

Records derived from an answer SHALL be journaled with the supplying actor, and
their confidence class SHALL be derived from that actor: a human supplier keeps
the class the capturing engine states for human participation, and any
non-human supplier SHALL yield `simulated`. No answer-derived record SHALL be
journaled with `actor.kind: human` unless the answer came from a human
supplier.

#### Scenario: Terminal answer stays human

- **WHEN** a human types an interview answer at the CLI prompt
- **THEN** the port returns that text with a human actor, and the record the engine appends carries `actor.kind: human` and the engine's human confidence class

#### Scenario: Brokered answer keeps its real supplier

- **WHEN** an answer reaches an engine through a port that received it from a non-human client
- **THEN** the record the engine appends carries that client's actor with `actor.kind: agent` and confidence class `simulated`, and nothing in the ledger attributes the answer to a human
