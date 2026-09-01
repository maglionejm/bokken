# Proposal: add-cost-telemetry

## Why

The Fusion cost optimization needs a measuring stick before any lane
changes: r5 cost $120.55 and the driver (persona_turn carrying the full
corpus, zero cache reads) was only visible via ad-hoc journal scripts.

## What Changes

- New verb `bokken costs <name>`: deterministic replay report - per
  stage x prompt_id x routing class: calls, input/output/cache-read
  tokens, list-price estimate, cache hit-rate; `--json` for scripts.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli`: costs verb.

## Impact

`src/bokken/cli/app.py`, `src/bokken/report/context.py` (shared price
table), tests.
