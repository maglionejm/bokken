# Contributing

Bokken uses spec-driven development with [OpenSpec](https://github.com/Fission-AI/OpenSpec).

## Workflow

1. **Propose** — every behavior change starts as a change under
   `openspec/changes/<change-id>/` with `proposal.md`, `specs/` deltas,
   `design.md` (when non-trivial), and `tasks.md`. Use `/opsx:propose` from
   Claude Code or write the artifacts by hand following the templates.
2. **Validate** — `openspec validate --strict` must pass before implementation
   starts.
3. **Apply** — implement against `tasks.md`, checking off tasks as they land.
4. **Archive** — `/opsx:archive` folds the deltas into `openspec/specs/`.

## Definition of done

```sh
make check
```

runs ruff (lint + format check), pytest, and `openspec validate --strict`.
All three must pass. New behavior requires new or updated scenarios in the
relevant spec delta and tests that exercise them.

## Ground rules

- Read `CLAUDE.md` (project constitution) before proposing changes.
- The Journal schema is versioned; changes to it always go through a spec
  delta with a migration note.
- No new runtime dependency without a rationale recorded in a `design.md`.
- Code, comments, and docs in English.
