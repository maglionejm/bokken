# Proposal: restructure-reports

## Why

Founder review of the v0.2.0 deliverables: the reports lack an explanation of
what actually ran (which agents, which personas, doing what, in what order),
stage sections do not follow a consistent Activity -> Process -> Output
structure, and the HTML is not consumable enough for humans - it needs to be
readable, graphical, and animated.

## What Changes

- Both formats open with a "How this run worked" anatomy: the executed
  sequence, the persona cast (name, role, segment, panel), the system agents
  (facilitator, ui-walker, lenses, skeptic), and the models each class ran on.
- Every stage section is structured as three labeled blocks: Agents &
  activity (who did what, with call counts), Process (the method applied),
  Output (the results).
- HTML overhaul: scroll progress, stat chips, persona cards, Chart.js
  charts (assumption register, opportunity ranking, cost by model),
  count-up animations, section reveals.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `report`: anatomy + stage structure requirements.

## Impact

`src/bokken/report/{context,page,deck}.py`, tests.
