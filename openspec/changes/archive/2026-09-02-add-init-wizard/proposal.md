# Change: add-init-wizard

## Why

Issue #27 (P0 onboarding): the distance from `pip install bokken` to a real
first run is too long — a new user has to reverse-engineer the Brief schema
from docs before anything happens. A guided `bokken init` that emits a valid
brief file from a proven template collapses that distance to two commands.

## What Changes

- New `bokken init` verb: pick one of three brief templates
  (`saas-retention`, `consumer-app`, `internal-tool`), answer a handful of
  plain prompts (product name, problem space, segments, inputs), and get a
  validated `bokken-brief.json` written to disk.
- Non-interactive path: `bokken init --template saas-retention --out f.json`
  writes the template with clearly marked placeholders, no prompts.
- The verb always ends by printing the exact next commands
  (`bokken new ... --brief ...`, then `bokken run ...`).

## Impact

- Affected specs: `cli` (ADDED requirement)
- Affected code: `src/bokken/cli/app.py`, new `src/bokken/cli/templates.py`
