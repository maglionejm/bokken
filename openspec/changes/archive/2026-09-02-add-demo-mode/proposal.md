# Proposal: add-demo-mode

## Why

Today a visitor needs an API key and ~$25 before seeing any output — fatal
for launch traffic. Issue #27: one command, zero keys, under a minute, with
publication-grade output that doubles as the Page gallery.

## What Changes

- `bokken demo [name]`: a complete offline dojo run (no key, no network)
  against a dedicated DemoProvider with hand-crafted content for the
  fictional product "Lanzadera", grounded in bundled fixtures (mini repo
  with CSS tokens, KPIs, interview transcripts) so every citation resolves.
  Finalization produces the dossier and both reports; the verb ends with the
  report paths and a $0.00 receipt. Deterministic: same output every run.
- Honesty unchanged: simulated-run banner, journaled walkthrough skip,
  research debt in Spanish, iterate verdict with quantified confidence.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli`: demo verb.

## Impact

`src/bokken/demo/` (provider + fixtures, packaged), CLI verb, tests, Page
gallery (separate change).
