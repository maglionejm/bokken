# Change: showcase-demo-ui-tests

## Why

The published demo deliverables (gallery report + deck) skip the UI
walkthrough and per-feature functional tests — one of Bokken's flagship
capabilities — because the fixture product has no running instance. The
specimen a prospective user studies should show the whole machine.

## What Changes

- The Lanzadera fixtures gain a small static mock app (single-file SPA on the
  product's own design tokens, tab views for tomorrow's window / booking /
  settings) with one deliberate defect that mirrors the case's core insight:
  the on-time indicator shows "ventana cumplida" beside a 9-minute-late
  notice.
- `bokken demo` declares the mock as `app_url` over `file://`. When the `[ui]`
  extra is available the real walkthrough and per-feature tests run against it
  in a real browser — real screenshots, journaled `observed` evidence, one
  works / one broken / one unclear verdict. Without the extra the run keeps
  today's honest skip. Either way: no network, $0.00.
- The DemoProvider scripts the feature inventory, the stepper (parsing the
  live element digest for indices), and a quantified UI review.
- `make gallery` builds with the `[ui]` extra so the published report and deck
  include the feature cards, step logs, and screenshots.

## Impact

- Affected specs: `cli` (MODIFIED Demo verb requirement)
- Affected code: `src/bokken/demo/` (fixtures/app, provider, brief),
  `Makefile`, `docs/index.html` copy, demo tests
