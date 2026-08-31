# Design: add-ui-walkthrough

## Dependency: playwright (optional extra `ui`)

Real functional observation of a running app needs a browser; Playwright is
the maintained standard. It is an optional dependency group — the core
installs without it, the walker protocol is injectable, and tests use a fake
walker. When the runtime is missing the walkthrough degrades to journaled
research debt (degradation-honest, like every other missing input).

## Confidence class

Walkthrough facts are `observed` evidence — a real product was really
exercised — unlike persona utterances (`simulated`). The heuristic review is
a model interpretation over those observations and lives as an artifact, not
as evidence.

## Bounds

Entry page plus at most five same-origin nav targets, one screenshot each,
no form submission, no authentication flows: a first-contact functional
test, not a crawler.
