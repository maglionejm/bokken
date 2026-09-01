# Proposal: enrich-report-deliberation

## Why

Founder review of the r5 deliverables: the app-test detail is too thin
(verdict table only - no steps, findings, or per-feature screenshots),
images break outside the session directory, texts are long and not
action-oriented, quantification is sparse, and the agents' deliberation -
lens votes, skeptic challenge, kata iteration, dissent - is journaled but
invisible.

## What Changes

- Reports SHALL be self-contained: HTML screenshots embedded as data URIs.
- The UI review section becomes per-feature cards: verdict, finding, the
  executed step log, and that feature's end-state screenshot.
- New "Deliberation" section in both formats: convergence lens votes
  (verdict / effort / first slice / position per lens), the skeptic
  challenge verbatim, Kata moves executed and suppressed, decision criteria
  and dissent.
- Action orientation: each stage header carries quantified stat chips, and
  the report closes with a "Next actions for the founder" list derived from
  broken feature findings, the recommendation's next step, and open
  research debt.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `report`: UI review detail, deliberation section, self-contained images,
  action orientation.

## Impact

`src/bokken/report/{context,page,deck}.py`, tests.
