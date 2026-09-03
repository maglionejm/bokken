# Tasks

- [x] Add the typed read path on `Event`: `typed_payload` returning the
      `TAXONOMY` model, `payload_as(Model)` narrowing it for static typing and
      raising on the wrong payload class, parsed once during validation and
      cached in a private attribute so it cannot reach the hash.
- [x] Keep `Event.payload` the untouched raw mapping and document it as the way
      out for generic readers; verified by asserting a record with an undeclared
      key re-serializes byte-identically and re-hashes to its stored hash.
- [x] Make payload validation strict on append and tolerant on read via a
      validation context passed by `parse_line`; reject undeclared keys at any
      nesting depth before the record is written.
- [x] Declare the extension keys producers write today in `EXTENSION_KEYS`,
      derived from a sweep of every payload written by the whole test suite, and
      add the checked `Event.extension(key)` accessor.
- [x] Record in the spec why extension keys are a key registry and not typed
      fields: the payload-normalization merge materializes declared defaults, so
      adding a defaulted field changes the recomputed hash of every earlier
      record and locks the operator out of their own session.
- [x] Migrate `dossier/model.py` to the typed accessor, including the
      confidence-class and synthetic-label logic, and `report/context.py`'s demo
      detection off hand-parsed JSON.
- [x] Migrate the honesty invariants inside the `Event` validator itself off
      string keys onto the parsed payload.
- [x] Commit a fixture journal produced before this change and assert its chain
      verifies, its hashes are unchanged, it replays to the same state, its
      undeclared keys and its typo read back, and it still builds a dossier.
- [x] `make check` green.
