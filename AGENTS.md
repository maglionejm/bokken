# AGENTS.md

Bokken is an agentic harness that runs the Design Thinking loop
(Empathize → Define → Ideate → Prototype → Test) as an executable,
event-sourced, governed process, consumed via CLI and MCP. No GUI.

## Dev loop (offline)

`make check` (ruff + pytest + `openspec validate --strict`) is the definition
of done. The full test suite runs against a fake provider — **no API key and
no network needed**. Run it before you conclude any change.

## Where the seams are

Three halt seams gate everything external, so a run is deterministic and
testable offline:

- **the input port** — founder/human input (CLI prompt or MCP mailbox);
- **the panel** — corpus, citations, grounding, governance firewalls;
- **the `ModelRouter`** (`src/bokken/models/router.py`) — the *only* place an
  LLM is invoked; stage/kata code never touches a provider SDK.

`src/bokken/contract.py` is the shared-shape boundary: one contract for the
CLI `--json` output and MCP tool results.

## How work flows

Spec → implement → review → document, spec-driven via OpenSpec
(`/opsx:propose` → `/opsx:apply` → `/opsx:archive`). Repo teammates live in
`.claude/agents/`.

## Running the teammates as a team

The four `.claude/agents/` definitions (`spec-writer`, `implementer`,
`reviewer`, `docs-auditor`) double as Agent Team members. Agent Teams is
experimental and enabled for this repo via
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` — open
Claude Code from the repo root so the setting and the named types load. Then
ask the lead in plain English, e.g. *"spawn spec-writer, implementer,
reviewer, and docs-auditor as a team and coordinate through the shared task
list."* The three writing teammates carry `isolation: worktree` so their git
work stays conflict-free; the reviewer is read-only and works the live tree.
Drive them from the lead session: ↑/↓ to select a teammate, Enter to view and
message it, `@name` to talk to one, `Ctrl+T` for the shared task list. One
team per session; re-spawn after a resume (in-process teammates don't
persist). Releases stay a human decision regardless of who did the work.

## Two golden rules

1. **Every behavior fix ships with its test in the same commit.** A dropped fix
   is invisible without one.
2. **Docs follow code.** In a docs task, report code smells — do not fix them.

## Start here

- [CLAUDE.md](CLAUDE.md) — the constitution (non-negotiables).
- [docs/codebase-map.md](docs/codebase-map.md) — the navigation map.
- [docs/gotchas.md](docs/gotchas.md) — hard-won failure modes.
- [docs/recipes.md](docs/recipes.md) — task cookbooks.
