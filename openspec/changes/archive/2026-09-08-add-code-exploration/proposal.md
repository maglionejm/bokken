# Change: add-code-exploration

## Why

Adapted from the exploration discipline in "build-software-with-style"
(enterprise template): sources carry declared evidence roles, and current
behavior is registered as typed, cited findings before design begins. Bokken
shipped raw code lines to personas with no structured read of what the
product does today; desired outcomes were framed against guesses.

## What Changes

- Corpus context headers declare each source kind's evidence role (code
  establishes implemented behavior, not desired intent; metrics measure
  current behavior; discussions are reported intent; documents stated
  intent) so every consumer inherits the epistemology.
- Empathize opens with code exploration when code sources exist: one
  cognition-lane call maps 4-10 current capabilities (actor + trigger +
  observable outcome), each citation-validated against the corpus and
  journaled as `interpretation.derived` kind `current_capability`
  (citations extension key; capabilities whose citations all fail are
  journaled ungrounded).
- The capability map feeds the walkthrough's feature inventory
  (feature_inventory v2), replacing regex routes as the primary signal of
  what to test.
- Journal invariant refined: an interpretation is grounded by refs to
  journal events OR validated corpus citations; with neither it must say
  ungrounded.

## Impact

- Affected specs: `stages` (ADDED), `panel` (MODIFIED context), `journal`
  (MODIFIED invariant)
- Affected code: `stages/exploration.py` (new), `empathize.py`,
  `walkthrough.py`, `ui_tests.py`, `panel/corpus.py`, `journal/schema.py`,
  prompts, demo/test fakes
