# Proposal: add-feature-functional-tests

## Why

The walkthrough inventories screens but does not exercise the product: the
founder needs each functionality actually tested - entered, interacted
with, and judged - not just screenshotted.

## What Changes

- After the crawl, a bounded feature inventory is derived from docs +
  routes + live DOM; each feature runs a bounded agentic interaction loop
  (model-chosen click/fill/navigate/conclude over a digest of interactive
  elements; demo values only; destructive controls excluded) ending in a
  per-feature verdict (works/broken/unclear) with step log and end-state
  screenshot.
- Artifacts `ui_feature_tests.md` + `.json`; steps journaled as observed
  evidence; the UI review consumes the results.
- Reports: per-feature results table (HTML) and verdict bullets (deck).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize walkthrough gains per-feature functional testing.
- `report`: UI review section gains the results table.

## Impact

`src/bokken/stages/ui_tests.py` (new), walkthrough wiring, prompts,
schemas, report renderers, fakes/tests, docs + site.
