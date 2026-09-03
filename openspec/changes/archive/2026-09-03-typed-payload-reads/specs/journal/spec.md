# journal Specification Delta

## MODIFIED Requirements

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
