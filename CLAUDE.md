# CLAUDE.md — project constitution

Bokken is an agentic harness for Design Thinking: the Empathize → Define →
Ideate → Prototype → Test loop as an executable, event-sourced, governed
process, consumed via CLI and MCP. No GUI.

## Non-negotiables

1. **Journal first.** The append-only JSONL Journal is the single source of
   truth. Session state is always derived by replay. Never write session state
   anywhere else; never mutate or delete journal records.
2. **Everything is an event.** LLM calls, facilitation moves, stage
   transitions, decisions (with dissent), evidence, ideas, artifacts — all land
   in the Journal with provenance.
3. **Honesty rules.** Synthetic contributions are labeled `simulated` at the
   record level. Confidence classes (`observed | reported | assumed |
   simulated`) propagate to everything derived from them. Never launder
   simulated research into "user insights".
4. **No silent self-escalation.** Dojo runs cannot expand their own brief,
   contact real humans, or publish externally. Web research (read-only) runs
   only when the brief declares `allow_web_research: true`, and its findings
   are `reported` evidence with cited URLs. Stopping rules terminate runs;
   the stopping reason is a Journal event.
5. **Own the loop.** The DT state machine is hand-written, explicit Python.
   Do not introduce LangGraph/LangChain-class dependencies.
6. **Keep it light.** Prefer stdlib. Every new dependency needs a reason in a
   design.md.
7. **Test rides with the fix.** Every behavior-visible fix ships with its test
   in the *same commit* — a dropped fix is invisible without one.
8. **Docs follow code.** Docs are corrected to match the code, never the
   reverse; in a docs task, report code smells, do not fix them.

## Workflow

- Spec-driven via OpenSpec. New behavior starts as a change proposal under
  `openspec/changes/` (`/opsx:propose`), is implemented via `/opsx:apply`,
  reviewed, documented, and archived via `/opsx:archive`.
- `make check` (ruff + pytest + `openspec validate --strict`) is the
  definition of done. The suite runs fully offline against a fake provider —
  no API key, no network. Do not conclude work with `make check` failing.
- Three halt seams gate everything external so a run stays deterministic and
  testable: the **input port** (founder/human input), the **panel** (corpus,
  citations, grounding, governance), and the **`ModelRouter`** (the only place
  an LLM is invoked). `contract.py` is the shared-shape boundary: one contract
  for the CLI `--json` output and MCP tool results.
- Releases are a human decision: a version-gated tag must equal `__version__`
  must equal `server.json`, and cadence is strategic (tag at a
  theme/milestone/security boundary, not per-PR). Commit as the personal
  `maglionejm` git identity in this repo.
- Repository language is English. CLI output is plain and utilitarian — no
  emojis, no decorative Unicode.

## Working here

New to the repo? Read [AGENTS.md](AGENTS.md), then
[docs/codebase-map.md](docs/codebase-map.md) (navigation),
[docs/gotchas.md](docs/gotchas.md) (failure modes), and
[docs/recipes.md](docs/recipes.md) (task cookbooks).

## Stack

Python ≥ 3.12 with uv. Pydantic v2 (schemas), Typer + Rich (CLI), `mcp`
(MCP server), `anthropic` (LLM; research/challenge classes on `claude-fable-5` at effort high
with server-side fallback to `claude-opus-4-8`; cognition/generation on
`claude-opus-5` adaptive thinking at effort high; the delegated `sidekick`
lane (verbatim corpus reads, mechanical UI stepping) on `claude-sonnet-5`;
`claude-haiku-4-5` only for the lightweight extraction routing class and
never on any other lane). Tests
with pytest; LLM calls are always behind the `ModelRouter` seam so tests can
run with a fake router — never call the Anthropic SDK directly from stage or
kata code. Optional extras stay optional: `[ui]` (playwright + beautifulsoup4)
for walkthrough/feature tests, `[interview]` (twilio) for remote validation
interviews, `[openai]` for the OpenAI provider; core installs and runs
without them, degrading honestly.

## Agent team

Four repo-defined teammates live in `.claude/agents/` and may run in parallel
(worktree-isolated) on independent work: `spec-writer` (OpenSpec packages,
never touches src), `implementer` (code+tests to a green `make check`, never
pushes or tags), `reviewer` (read-only verified findings), `docs-auditor`
(docs follow code; reports code smells, never fixes them). Split work along
the spec -> implement -> review -> document seam; merge points are PRs, and
releases stay a human decision regardless of who did the work.

