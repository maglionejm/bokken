# Contributing

Thanks for the interest — feedback from real runs is exactly what this
project needs right now.

## The fastest way to help

Run Bokken against a real product and tell us what happened:

```sh
uvx bokken demo      # see a complete run first — offline, $0.00
uvx bokken init      # then write a brief for your own product from a template

uvx bokken new my-run --brief bokken-brief.json --mode dojo --repo ./your-app --app-url http://localhost:PORT
uvx bokken run my-run
```

Then open a **Run feedback** issue with the verdict, what surprised you, and
what the reports got right or wrong. The journal (`.bokken/sessions/<name>/`)
never leaves your machine — share only what you choose to paste.

## Code contributions

Bokken uses spec-driven development with
[OpenSpec](https://github.com/Fission-AI/OpenSpec).

1. **Propose** — every behavior change starts as a change under
   `openspec/changes/<change-id>/` with `proposal.md`, `specs/` deltas,
   `design.md` (when non-trivial), and `tasks.md`. Use `/opsx:propose` from
   Claude Code or write the artifacts by hand following the templates.
2. **Validate** — `openspec validate --strict` must pass before implementation
   starts.
3. **Apply** — implement against `tasks.md`, checking off tasks as they land.
   The whole harness runs offline against the fake provider — no API key
   needed for development.
4. **Archive** — `/opsx:archive` folds the deltas into `openspec/specs/`.

## Definition of done

```sh
make check
```

runs ruff (lint + format check), pytest, and `openspec validate --strict`.
All three must pass. New behavior requires new or updated scenarios in the
relevant spec delta and tests that exercise them.

## Ground rules

- Read `CLAUDE.md` (project constitution) before proposing changes —
  journal-first, everything is an event, honesty rules, no silent
  self-escalation, keep it light. PRs that bend those will be asked to unbend.
- The Journal schema is versioned; changes to it always go through a spec
  delta with a migration note.
- No new runtime dependency without a rationale recorded in a `design.md`.
- Code, comments, and docs in English.

## Project status

Active development is paused while real-user feedback accumulates. Issues
are triaged; small fixes and doc PRs are merged; larger features are
collected for the next cycle.
