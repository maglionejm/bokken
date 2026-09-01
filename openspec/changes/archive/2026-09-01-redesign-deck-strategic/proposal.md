# Proposal: redesign-deck-strategic

## Why

Founder review: the deck read as text dumps. The house reference
(Vatios_Next5_Workshop.pptx) sets the bar: real tables with dark headers
and zebra rows, colored verdict cells, HILL banners, chip rows, and an
action-oriented close.

## What Changes

Presentation-only rewrite of the deck renderer in the workshop grammar
(all report requirements unchanged): executive-summary decision table
(What/Result/So what) with validation-guardrail banner, stage chip row +
cast, UI tests as a verdict-colored table with a broken-feature screenshot,
Ulwick ranking table with banded colors, concept slide as HILL banner +
"why it won" lens positions + dissent + hypothesis bar, sourced research
tables, register table with colored verdicts, deliberation slide, numbered
next-actions table, appendix with the paper trail.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none - presentation only; skip_specs)

## Impact

`src/bokken/report/deck.py`, `context.py` (Hill/hypothesis parse).
