# Proposal: add-ui-walkthrough

## Why

When a run is given a real application, the report must include a documented
functional test of its UI — observed facts about what the product actually
does at first contact, with constructive feedback — as first-class research
input and as a report section. Today Bokken only reads the repo as text.

## What Changes

- New optional brief input `app_url`: a running instance of the product.
- Empathize (dojo) performs a functional UI walkthrough when `app_url` is
  set: a browser walker visits the app (entry page plus same-origin nav
  links, bounded), records observed facts per screen (title, headings,
  primary actions, forms, console errors, load time) and a screenshot; facts
  are journaled as `observed` evidence (this is real product observation,
  not simulation), screenshots as `ui_screenshot` artifacts; a research-
  class model call turns the observations into a constructive heuristic
  review (`ui_review` artifact) written for the founder. When `app_url` is
  absent or the browser runtime is unavailable, the walkthrough is skipped
  as journaled research debt — never silently.
- Report: both formats gain a "Functional UI review" section when a
  `ui_review` artifact exists (the HTML embeds the screenshots).
- CLI: `bokken new --app-url <url>`.
- Optional dependency group `ui` (playwright); the walker is injectable so
  tests run offline.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize engine gains the walkthrough behavior.
- `report`: UI review section requirement.
- `cli`: `--app-url` input flag.

## Impact

`src/bokken/journal/schema.py` (BriefInputs), `src/bokken/stages/
{walkthrough,empathize}.py`, `src/bokken/models/prompts.py`
(`empathize/ui_review`), `src/bokken/report/{context,page,deck}.py`,
`src/bokken/cli/app.py`, `pyproject.toml` (`[ui]` extra), tests.
