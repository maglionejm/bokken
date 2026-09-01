# Proposal: deepen-ui-walkthrough

## Why

The v0.2.0 walkthrough only reached the home page and the admin console:
discovery was limited to nav/header links. A documented functional test must
cover the product, not its front door — and when the code is available, the
code knows the routes.

## What Changes

- Screen discovery from three sources: live DOM (all same-origin anchors,
  path-deduplicated), code route definitions (parameterless GET routes),
  and template links; union visited up to 12 pages.
- Richer per-screen facts via static HTML analysis (BeautifulSoup):
  heading structure, unlabeled inputs, images without alt, forms.
- Desktop and mobile screenshots per screen.
- The review must state its coverage (visited vs discovered).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize walkthrough requirement deepened.

## Impact

`src/bokken/stages/walkthrough.py`, `[ui]` extra gains beautifulsoup4,
prompt `empathize/ui_review` v2, tests.
