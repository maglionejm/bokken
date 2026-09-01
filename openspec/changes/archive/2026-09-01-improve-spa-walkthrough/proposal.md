# Proposal: improve-spa-walkthrough

## Why

vatios-r4 walked only 2 screens: the declared repo pointed at a subdirectory
without route definitions, and the product is a one-page app whose
navigation is JS tabs, not anchors. Real products are often SPAs; the
functional test must exercise them.

## What Changes

- Walker activates tab-like controls (`[role=tab]`, nav/tab-class buttons)
  on each page, capturing each resulting state as its own observation with
  screenshot (bounded by the page budget).
- Route discovery scans from the repository's version-control root when the
  declared repo path is a subdirectory.
- Operating docs: point `--repo` at the repo root.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize walkthrough discovery requirement.

## Impact

`src/bokken/stages/walkthrough.py`, tests, docs/operating.md.
