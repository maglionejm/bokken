# kata Specification

## Purpose
The Kata is Bokken's facilitation move library: every intervention the harness makes in a session is a named, parameterized, budgeted move with a defined trigger, logged like a tool call — so facilitation itself is drilled, repeatable, and inside the audit scope.

## Requirements

### Requirement: Move registry

The Kata SHALL be a registry of moves, each declaring: a stable `move_id`, a human-readable intent, the stages where it applies, its trigger (a predicate over replayed session state), its parameters schema, its surface adaptation for each mode (terminal prompt/checkpoint in Founder mode; autonomous injection in Dojo mode), and its per-session budget (maximum executions, possibly unlimited). The MVP registry SHALL include at least: `stage_contract` (open a stage by stating goal, method, and exit bar), `hmw_reframe` (reframe a solution-shaped problem statement), `assumption_flag` (mark an unsupported quantified claim as unvalidated), `timebox_pivot` (propose moving from divergence to convergence on idea-rate/novelty decay), `synthesis_readback` ("here's what I heard — correct me" at stage exit), `devils_advocate` (clearly-labeled counter-position when consensus forms with zero dissent), `parking_lot` (park an off-scope thread), `loopback_proposal` (propose returning to an earlier stage when test/define contradictions are detected), and `close_and_commit` (extract binding commitments with owners at run end).

#### Scenario: Registry is introspectable

- **WHEN** the move registry is listed
- **THEN** every MVP move above is present with id, intent, stages, trigger description, parameter schema, and budget

#### Scenario: Move applies only in its stages

- **WHEN** `timebox_pivot`'s trigger conditions occur outside `ideate`
- **THEN** the move is not executed and, if evaluated, its suppression is journaled with reason `out_of_stage`

### Requirement: Every move execution or suppression is journaled

Whenever a move's trigger fires, the Kata SHALL either execute the move — journaling `facilitation.move_executed` with `move_id`, trigger snapshot, parameters, and outcome — or suppress it — journaling `facilitation.move_suppressed` with the reason (`budget_exhausted`, `out_of_stage`, `mode_config`, or `superseded`). No move SHALL affect the session without its execution event.

#### Scenario: Executed move is auditable

- **WHEN** `assumption_flag` fires on an unsupported claim
- **THEN** a `facilitation.move_executed` event records the claim reference and the created assumption-register entry in `refs`

#### Scenario: Budget-exhausted move is suppressed visibly

- **WHEN** a move whose budget is spent triggers again
- **THEN** it does not execute and a `facilitation.move_suppressed` event records `budget_exhausted`

### Requirement: Move budgets

Each move SHALL enforce its per-session budget counted from journaled executions, so budgets survive resume. Budgets SHALL be configurable per session at creation within registry-defined maxima.

#### Scenario: Budget survives resume

- **WHEN** a session that executed `devils_advocate` twice (budget 3) is resumed
- **THEN** the remaining budget is 1, derived from replay

### Requirement: Tone contract

All move outputs rendered to a user or panel SHALL be neutral, warm, and brief; critiques SHALL be depersonalized (about claims and options, never about persons), and counter-positions injected by `devils_advocate` SHALL be explicitly labeled as deliberate counter-positions.

#### Scenario: Depersonalized critique

- **WHEN** `assumption_flag` renders its output for an unsupported claim made by a named participant
- **THEN** the rendered text addresses the claim ("this claim is unvalidated"), names no person as wrong, and the devil's-advocate label rule is honored for counter-positions
