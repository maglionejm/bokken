# journal Specification

## Purpose
The Journal is Bokken's event-sourced process ledger: an append-only, tamper-evident record of everything that happens in a Design Thinking session, from which session state, audits, and the Session Dossier are derived. It records at the moment of occurrence, links every artifact to its evidence, preserves dissent and dead ends, and separates observation from inference.

## Requirements

### Requirement: Event envelope

Every journal record SHALL be a single JSON object with the envelope fields: `schema_version` (string, `"1"` for this spec), `seq` (session-monotonic integer starting at 1, no gaps), `id` (globally unique string), `ts` (UTC timestamp, ISO 8601 with timezone), `session_id`, `type` (dot-namespaced event type, e.g. `evidence.captured`), `stage` (one of `intake | empathize | define | ideate | prototype | test | complete` or `null` for stage-independent events), `actor` (object with `kind` ∈ `human | agent | system`, `name`, and — when `kind=agent` — `model` and `persona_id` where applicable), `payload` (type-specific object), and `refs` (possibly empty list of event `id`s this event derives from or responds to).

Payload validation SHALL be asymmetric: strict on append, tolerant on read.

On append, the system SHALL reject a payload carrying any key, at any nesting
depth, that is neither a declared field of the event type's payload model nor a
declared extension key for that type, and SHALL do so before the record is
written. The ledger is append-only and records may never be mutated or
deleted, so a key misspelled on append cannot be corrected — only superseded —
and rejecting the append is the only point at which it can be prevented.

On read, the system SHALL NOT reject a persisted record for carrying payload
keys it does not declare, and SHALL preserve them verbatim. This covers both a
journal written by a newer revision that declares more keys and a record whose
key was misspelled before the write path became strict: an already-written
record is a fact about the run, not something a reader may refuse or silently
repair.

The system SHALL expose each record's payload as its typed taxonomy payload
model alongside the raw mapping, so readers derive state by attribute access
over the declared vocabulary rather than by string key. Reading a payload as a
payload class the event type does not carry SHALL fail loudly rather than yield
absent values. The raw mapping SHALL remain available and SHALL NOT be altered
by the typed view, so undeclared keys stay reachable through both and survive a
read-modify-write cycle. Reading a declared extension key by name SHALL fail
when that key is not declared for the event type.

#### Scenario: Well-formed event is accepted

- **WHEN** an event with all envelope fields valid is appended
- **THEN** it is persisted with the next `seq` value and can be read back byte-identical

#### Scenario: Malformed event is rejected before persistence

- **WHEN** an append is attempted with a missing envelope field, an unknown `stage`, or a non-UTC timestamp
- **THEN** the append fails with a validation error and nothing is written to the ledger

#### Scenario: Unknown payload fields are tolerated on read

- **WHEN** a journal written by a newer minor revision contains extra payload fields
- **THEN** replay and queries succeed, preserving unknown fields opaquely (forward compatibility), and re-serializing the record reproduces those fields and its original hash

#### Scenario: A misspelled payload key is refused on append

- **WHEN** an append is attempted with an `interpretation.derived` payload
  carrying `sevrity` alongside the declared fields
- **THEN** the append fails with an error naming the undeclared key, and
  nothing is written — including when the misspelled key is nested inside
  another payload object, such as `brief.target_segements`

#### Scenario: A declared extension key is accepted on append

- **WHEN** a persona answer is captured with the declared extension keys
  `segment` and `grounding`
- **THEN** the append succeeds, the keys are persisted verbatim, and reading
  them by name succeeds while reading `segmnet` raises

#### Scenario: Readers derive state from the typed payload

- **WHEN** the dossier is built from a journal
- **THEN** every payload it reads is obtained as that event type's payload
  model, so a renamed or misspelled field is a type error rather than a
  silently missing value in the dossier's confidence and synthetic labels

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

### Requirement: Append-only durable storage with hash chain

The Journal SHALL be stored as one JSONL file per session (`journal.jsonl` in the session workspace). Appends SHALL be atomic (a reader never observes a partial line), flushed durably before the append call returns, and strictly ordered by `seq`. Each record SHALL carry `prev_hash` (the `hash` of the previous record, or the fixed genesis value for `seq=1`) and `hash` (SHA-256 over the record's canonical serialization excluding `hash` itself). Records SHALL never be mutated or deleted; corrections are new events referencing the corrected event.

Because chain verification recomputes each record's hash from its *validated*
payload, and validation materializes a payload model's declared defaults into
that payload, reading a record SHALL NOT change the payload it was written
with. Adding a defaulted field to an existing payload model violates this: the
default is injected when an older record is re-read, its recomputed hash no
longer matches the stored one, and every session written before the change
fails verification and can no longer be opened for writing. Promoting an
untyped extension key to a declared payload field is therefore a
schema-versioning change and SHALL NOT be done as an incidental edit.

#### Scenario: Interrupted process leaves a readable ledger

- **WHEN** the process is killed at an arbitrary point during a run
- **THEN** re-opening the session finds a journal whose every line parses, whose `seq` is contiguous, and whose hash chain verifies end-to-end

#### Scenario: Tampering is detectable

- **WHEN** any persisted record's bytes are altered after the fact
- **THEN** chain verification reports the first broken link's `seq` and fails

#### Scenario: Concurrent writers are prevented

- **WHEN** a second process attempts to open the same session for writing while one holds it
- **THEN** the second open fails fast with a clear "session is locked" error rather than interleaving writes

#### Scenario: A session written before a schema change still verifies

- **WHEN** a journal produced by an earlier revision — carrying undeclared
  payload keys, and records written without fields whose declared defaults that
  revision materialized — is read by the current one
- **THEN** its chain verifies, every record's recomputed hash equals its stored
  hash, replay yields the same state, and no record is rewritten

### Requirement: Replay to session state

The system SHALL derive session state exclusively by folding the journal in `seq` order into a typed state: current stage, session mode and brief, pending gate (if any), evidence index by confidence class, insight/POV list with grounding links, idea lineage graph, assumption register, decision log with dissent, budget counters (tokens spent per routing class), and stop status. Replay SHALL be deterministic: the same journal always yields the same state.

Budget counters SHALL count every token bucket the provider billed — uncached
input, output, cache read, and cache write — at face value, because budgets
are expressed as token counts and provider adapters report the cached prompt
prefix disjointly from `input_tokens`. No billed bucket SHALL be invisible to
the meter, and the meter SHALL NOT apply prices or weights: pricing belongs to
the cost report.

#### Scenario: Resume reconstructs exactly where the run left off

- **WHEN** a session that stopped mid-`ideate` is reopened and replayed
- **THEN** the derived state reports stage `ideate`, the same idea lineage and budgets as before the stop, and the run continues without re-executing prior events

#### Scenario: Replay is pure

- **WHEN** the same journal file is replayed twice
- **THEN** both derived states are equal field-for-field

#### Scenario: A cached prompt prefix is not invisible to the budget

- **WHEN** a `model.called` event reports 5,000 input, 500 output, and 195,000
  cache-read tokens
- **THEN** `tokens_spent` for that routing class is 200,500, and a session
  budget of 100,000 total tokens is exhausted

### Requirement: Session workspace and addressing

Sessions SHALL live under a workspace root (default `./.bokken/sessions/`, overridable via the `BOKKEN_HOME` environment variable), one directory per session named by a slug of the session name. A session SHALL be addressable by its name for all operations. Creating a session with an existing name SHALL fail; listing SHALL enumerate sessions with name, current stage, mode, and last-event timestamp derived from their journals.

#### Scenario: Create then address by name

- **WHEN** a session `mars-lander` is created and later any operation references `mars-lander`
- **THEN** the operation resolves to the same workspace directory and journal

#### Scenario: Duplicate name is refused

- **WHEN** `bokken new` is invoked with a name that already exists in the workspace
- **THEN** creation fails with an error suggesting `run`/`status` for the existing session

### Requirement: Ledger queries

The Journal SHALL support read queries filtered by any combination of event type (exact or family prefix), stage, actor kind, and `seq`/time range, returned in `seq` order, plus a follow mode that yields new events as they are appended. Query results SHALL be exposable as machine-readable JSON.

#### Scenario: Filter by family and stage

- **WHEN** a query requests family `option.*` within stage `ideate`
- **THEN** exactly the matching events are returned in `seq` order

#### Scenario: Follow mode streams new events

- **WHEN** a follower is attached and a new event is appended
- **THEN** the follower receives that event without re-reading the whole file
