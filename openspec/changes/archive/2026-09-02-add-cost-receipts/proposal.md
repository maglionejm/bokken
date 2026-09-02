# Change: add-cost-receipts

## Why

Issue #27 (P0 onboarding): cost anxiety is the top adoption blocker for a
tool that spends real tokens. Today the spend is only visible if the user
knows to ask (`bokken costs`). The run itself should frame the cost before
it starts and account for it when it stops.

## What Changes

- `bokken run` prints a one-line cost framing before the loop starts: the
  session's token guardrail and the typical full-run cost range.
- When the loop halts (any halt reason), `bokken run` prints a receipt from
  the journaled model calls: session-to-date list-price cost, call count,
  and a pointer to `bokken costs <name>` for the breakdown.
- JSON mode carries the same numbers in the result payload instead of prose.

## Impact

- Affected specs: `cli` (ADDED requirement)
- Affected code: `src/bokken/cli/app.py` (run verb), reusing
  `report/context.py` pricing helpers
