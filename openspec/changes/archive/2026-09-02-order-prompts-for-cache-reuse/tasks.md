# Tasks

- [x] Reorder `empathize/persona_turn` (corpus first) and `empathize/outcome_scores`
      (outcome list first), preserving the in-character, cite-the-line-span and
      abstain-honestly framing; verified by a prompt test asserting each
      instruction survives the reorder and the outcomes precede the persona.
- [x] Declare the cache split on `empathize/persona_turn` and bump it to v4;
      verified by a test rendering the turn for three personas over one corpus
      and asserting one byte-identical prefix, three distinct suffixes, and the
      corpus before the question.
- [x] Declare the cache split on `ideate/converge` (v3) and `test/evaluate` (v3,
      artifact first); verified by a shared/varying parameter test covering every
      marked prompt, including that the marker changes no wire text.
- [x] Leave `empathize/outcome_scores` unmarked (v2) with the prefix-size
      rationale in the template comment; verified by the same shared/varying test
      listing only the templates that legitimately declare a split.
- [x] Memoize sidekick retrieval per (question, corpus) so every persona turn on
      a question gets the identical prefix; verified by a test asserting one
      sidekick call per distinct question and equal slices across repeats.
- [x] Raise `DELEGATE_THRESHOLD_CHARS` to 120k with the cached-corpus break-even
      recorded in the code; verified by the delegation tests, which now assert
      their corpora exceed the threshold constant instead of hard-coding a size.
- [x] `make check` green (ruff, 174 tests, `openspec validate --strict --all`).
