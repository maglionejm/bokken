# Proposal: add-wireframe-artifacts

## Why

The market converged on wireframe-as-code on real design tokens (v0,
Lovable), and the reference workshop shipped HTML mocks on the product's
own CSS. Bokken's prototypes stop at markdown.

## What Changes

- New artifact kind `wireframe_html`: one self-contained HTML mock built on
  the declared repo's real CSS tokens (sliced, budgeted); fidelity may pick
  it when the riskiest assumption is screen comprehension.
- The browser walker exercises the generated wireframe (observed evidence +
  screenshot); the test panel evaluates it like any prototype artifact.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Prototype engine kinds + exercise.

## Impact

schemas, prototype engine, prompts (artifact/fidelity v3), testing kinds,
fakes/tests.
