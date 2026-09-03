# Change: add-brief-autopilot

## Why

Issue #48: the distance from install to a good first run is dominated by
authoring the brief. The templates lowered the wall; drafting the brief from
the user's own repository removes it.

## What Changes

- `bokken init --from-repo PATH [--metrics FILE] [--yes]`: ingest the corpus
  through the existing pipeline (caps, suffix allowlist), one extraction-lane
  call for product facts, one cognition-lane call to draft the brief;
  per-field confirmation unless `--yes`; validated write; drafting cost
  disclosed and the scratch journal discarded (no session exists yet).

## Impact

- Affected specs: `cli` (MODIFIED Init wizard requirement)
- Affected code: `cli/autopilot.py` (new), `cli/app.py`, two `intake/*`
  prompts, two schemas
