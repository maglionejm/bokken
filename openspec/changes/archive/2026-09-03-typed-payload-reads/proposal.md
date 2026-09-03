# Proposal: typed-payload-reads

## Why

`journal/schema.py` defines a `TAXONOMY` that maps every event type to a typed
`Payload` subclass, and `Event`'s validator parses each payload against its
class on append. Nothing then *uses* those classes as types. Every reader in
the codebase indexes the raw dict by string key — `event.payload["confidence_class"]`,
`p.get("speaker")` — and the validator itself computes `parsed =
model.model_validate(self.payload)` only to throw the parsed object away and
merge it back into a plain dict. So a fully specified typed vocabulary over the
one file format the whole system is built on delivers no autocomplete, no
static checking and no rename safety. `dossier/model.py` is the sharpest case:
it is where confidence classes and synthetic labels are decided, so a
misspelled key there yields a dishonest dossier rather than an error.

There is a second problem on the other side of the same file. `Payload` sets
`extra="allow"`, which is correct for a tolerant reader — a field written by a
newer version must not break an older reader — but it applies on the write path
too. Appending an `interpretation.derived` payload carrying `"sevrity": "high"`
alongside the real fields is accepted today, and because the Journal is
append-only and records may never be mutated or deleted, that typo is immortal.

## What Changes

- Add a typed read path on `Event`: `typed_payload` returns the `TAXONOMY`
  model for the record's type, and `payload_as(Model)` narrows it for static
  typing, raising when the event type does not carry that payload class. The
  model is parsed once during validation and cached in a private attribute, so
  the typed read costs nothing and cannot affect the record hash.
- Keep `Event.payload` exactly as it is — the raw mapping, unknown keys
  included — as the documented way out for generic tooling and for the untyped
  extension keys. The typed accessor never rewrites it, so a read-modify-write
  cycle still cannot drop a key a newer Bokken wrote.
- Make payload validation asymmetric: **strict on append, tolerant on read.**
  `parse_line` passes a validation context that tolerates undeclared keys, so
  every persisted record still loads. Every other construction is a write, and
  a write carrying a key that is neither a declared field nor a declared
  extension key is rejected — at any nesting depth — before anything is
  appended.
- Declare the extension keys real producers write today in `EXTENSION_KEYS`
  (`segment`, `grounding`, `panel_kind`, `requested_model`, `config_overrides`,
  `private_thought`, the Ulwick scoring keys, and the rest), and add
  `Event.extension(key)`, which raises on a name that is not declared for the
  event type rather than returning `None` for a misspelling.
- Migrate the two largest readers, `dossier/model.py` and `report/context.py`,
  to the typed accessor, and migrate the honesty invariants inside the `Event`
  validator itself off string keys.
- Lock backward compatibility with a committed fixture journal produced before
  this change, asserting its chain still verifies, its hashes are unchanged, it
  still replays, and its typo still reads back.

Not in scope: the 63 append sites keep passing dicts. Typed construction on
write is a follow-up.

## The write-side trade-off

Tolerating unknown keys on append is the only place a typo can be stopped, so
the choice is between refusing them and merely reporting them. Reporting loses:
a warning does not stop the write, and the record is permanent either way.
Refusing them, however, is only viable if the keys producers legitimately write
are *known* — and a sweep of the whole suite found 20 distinct groups of
undeclared keys in live use across 9 event types, several of them load-bearing
(the empathize exit gate reads `segment`; the test-panel firewall reads
`panel_kind` and `persona_ids`; fallback provenance reads `requested_model`).

The obvious way to make them known is to promote them to typed fields. That is
the option this change deliberately does not take, because it would break every
existing session. `Event`'s validator normalizes the payload by merging
`parsed.model_dump(exclude_unset=False)` into it, which materializes declared
defaults into the stored record, and `verify_chain` recomputes each record's
hash from the *validated* payload. Adding one defaulted field to an existing
payload model therefore injects that default when an older record is re-read,
changes its recomputed hash, and breaks the chain — verified on this branch by
adding a single `str | None = None` field to `EvidenceCaptured`, after which the
fixture journal fails with `record hash does not match content` at seq 3. Since
`JournalStore.open` verifies before writing, the operator is locked out of their
own session.

So the extension keys are declared as a per-type key registry instead of as
model fields. It costs nothing on disk, changes no hash, needs no session
rewritten, and still lets the write path tell a known extension from a typo.
The cost is honest and stated: those keys have no attribute to autocomplete and
are read through `Event.extension`, and adding a new payload key now means
declaring it in `schema.py` — which for the system's single source of truth is
the change-controlled surface it should be. Promoting the registry to real
typed fields needs the payload-normalization merge fixed first (so reads stop
materializing defaults), which in turn needs the remaining raw-dict readers —
`replay.py` above all — moved onto the typed accessor. That is the follow-up
this change makes possible; the spec now records the constraint so the trap is
not rediscovered by breaking a user's session.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `journal`: payload validation is strict on append and tolerant on read; each
  record exposes its payload as its typed taxonomy model; promoting an
  extension key to a declared field is a schema-versioning change because it
  changes recomputed hashes.
- `dossier`: the dossier is built through the typed payload, so the confidence
  and synthetic-label logic cannot be defeated by a string-key typo.

## Impact

`src/bokken/journal/schema.py`, `src/bokken/dossier/model.py`,
`src/bokken/report/context.py` and their tests, plus a committed fixture
journal at `tests/journal/fixtures/legacy-session/`. No on-disk format change:
no record's bytes, keys or hash change, and existing sessions load, replay and
verify unchanged. The one behavioral change for producers is that an append
carrying an undeclared payload key now fails instead of persisting the typo.
