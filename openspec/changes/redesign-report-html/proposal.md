# Proposal: redesign-report-html

## Why

Founder review: the HTML needed a ground-up reshape, not incremental
patches - sections and formats rethought for human consumption.

## What Changes

Presentation-only rewrite of the HTML renderer (all existing report
requirements unchanged and still satisfied): app-shell layout with a fixed
numbered table-of-contents rail (scrollspy) and verdict chip; verdict-first
hero with animated stat strip; every section becomes a numbered chapter with
ghost numerals, kicker, and lede; the process arc becomes a timeline;
evidence carries colored confidence-class tags; cast cards gain avatars;
a verdict panel closes the story; print stylesheet. Charts, counters,
progress bar, A/P/O strips, and all content blocks carried over.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none - presentation only; skip_specs)

## Impact

`src/bokken/report/page.py` only.
