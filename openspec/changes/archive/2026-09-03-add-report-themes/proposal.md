# Change: add-report-themes

## Why

Issue #48: the deliverables had zero configurability (fixed palette, fixed
attribution), but Bokken's highest-value users forward the report and deck
to their own clients under their own name. Theming turns "a tool I use"
into "a deliverable I sell".

## What Changes

- `Theme` (brand color, dark variant, brand label, footer) with builtins
  `bokken` and `plain`, or a JSON file. Themes change chrome, never content;
  colors validated as hex.
- `bokken export --theme` per export; `bokken new --theme` journals the
  choice in the session config so regeneration is stable.
- v1 scope, stated plainly: the HTML report is fully themed (CSS custom
  property override + brand label + footer); the deck gets the themed
  footer/label while its palette stays fixed. Locale string tables land
  with the page decomposition in the refactor phase.

## Impact

- Affected specs: `report` (ADDED requirement)
- Affected code: `report/theme.py` (new), `page.py`, `deck.py`,
  `generate.py`, `cli/app.py`
