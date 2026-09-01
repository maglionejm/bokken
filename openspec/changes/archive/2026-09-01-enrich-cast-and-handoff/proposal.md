# Proposal: enrich-cast-and-handoff

## Why

The reference workshop (vatios_dt_workshop) worked with concrete personas
(Carmen, 54, Madrid...) and shipped decisions as slice plans with a
PR-train sequencing. Bokken's personas read as 'segment-1' and its handoff
stops at requirements.

## What Changes

- Casting: segment personas get vivid deterministic identities (seeded
  name/age/city/household) - flavor for role-play, honesty rules unchanged.
- Handoff: per-capability slice plans (S/M/L) + dependencies + package
  sequencing (build order with rationale), rendered into the proposal;
  specify prompt v3.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `panel`: casting requirement gains vivid identities.
- `handoff`: package generation gains slices/dependencies/sequencing.

## Impact

`src/bokken/panel/casting.py`, `src/bokken/handoff/{schema,render}.py`,
prompts, tests.
