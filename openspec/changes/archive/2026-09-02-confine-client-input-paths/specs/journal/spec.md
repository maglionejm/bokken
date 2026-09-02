# journal Specification Delta

## MODIFIED Requirements

### Requirement: Event taxonomy v1

The Journal SHALL support exactly the following event families and types in schema v1, and SHALL reject events whose `type` is not among them:

- `session.*`: `session.created` (brief, mode, config snapshot), `session.resumed`, `session.gate_requested`, `session.gate_resolved` (approve/reject + who), `session.stopped` (with `reason` ∈ `completed | budget_exhausted | novelty_floor | criteria_met | human_stop | error`).
- `evidence.*`: `evidence.captured` — an utterance, document span, data point, or synthetic-persona answer entering the record, with `source`, `confidence_class` ∈ `observed | reported | assumed | simulated`, and speaker/persona provenance; `evidence.abstained` — a persona or interviewee explicitly declining for lack of grounding (research debt); `evidence.input_rejected` — a declared corpus input that ingestion refused or capped (`path`, `reason`), so a grounding gap is on the record rather than a silent omission.
- `interpretation.*`: `interpretation.derived` — an insight, theme, or POV statement, a JTBD desired-outcome statement, a per-persona outcome score (importance/satisfaction), or a computed opportunity record (kinds `insight | theme | pov | hmw | desired_outcome | outcome_score | opportunity`), with `refs` pointing at supporting evidence or outcome events and a mandatory `ungrounded: true` flag when `refs` is empty.
- `option.*`: `option.created`, `option.built_on`, `option.merged`, `option.split`, `option.parked`, `option.killed` — the idea lineage graph; each carries contributor provenance and, for merge/kill, the surviving/killing option ids in `refs`.
- `decision.*`: `decision.recorded` — IBIS-style: the question at issue, the options on the table (`refs` to option events), the criteria applied, positions by named actor, the resolution, and explicitly recorded `dissent` (possibly empty list of `{actor, reservation}`).
- `assumption.*`: `assumption.registered` — an assumption entering the register, with statement, impact and uncertainty classes, and `refs` to the claims or options it derives from; `assumption.scored` — a test outcome for a registered assumption (`supported | contradicted | untested`) with `refs` to the assumption and the evaluating evidence.
- `facilitation.*`: `facilitation.move_executed` and `facilitation.move_suppressed` — a Kata move with `move_id`, trigger, parameters, and (for suppressed) the suppression reason; the agent is inside its own audit scope.
- `transition.*`: `transition.fired` — stage entry/exit and loop-backs, with `from_stage`, `to_stage`, `condition` (what fired it), and `refs` to the evidence/decision events that justified it.
- `model.*`: `model.called` — every LLM invocation, with model id, prompt identifier + content hash, routing class, token usage, request id, and outcome status.
- `artifact.*`: `artifact.generated` — a produced artifact (file path relative to the session workspace, artifact kind, content hash) with `refs` to the assumption/decision events it embodies.

#### Scenario: Unknown event type is rejected

- **WHEN** an append is attempted with `type` = `canvas.drawn` (not in taxonomy v1)
- **THEN** the append fails with an error naming the unknown type

#### Scenario: Simulated evidence carries its confidence class

- **WHEN** a synthetic persona's answer is captured as evidence
- **THEN** the stored event has `confidence_class: "simulated"` and persona provenance, and this cannot be omitted or overridden to `observed`

#### Scenario: Decision preserves dissent

- **WHEN** a decision is recorded with one participant registering a reservation
- **THEN** the persisted `decision.recorded` event contains that reservation verbatim in `dissent`, and replay exposes it on the decision log

#### Scenario: A contact and its outcome are one linked pair

- **WHEN** a run asks a real human for consent to be interviewed
- **THEN** `interview.consent_requested` is appended before the channel reaches them and the `interview.consent_resolved` that follows carries the outcome and `refs` back to that request

#### Scenario: Rejected corpus input is on the record

- **WHEN** a declared input is refused by ingestion (outside the authorized input root, missing, unsupported suffix, or over a size cap)
- **THEN** an `evidence.input_rejected` event names the path and the reason, so the missing grounding is auditable
