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

## Workflow

- Spec-driven via OpenSpec. New behavior starts as a change proposal under
  `openspec/changes/` (`/opsx:propose`), is implemented via `/opsx:apply`, and
  archived via `/opsx:archive`.
- `make check` (ruff + pytest + `openspec validate --strict`) is the
  definition of done. Do not conclude work with `make check` failing.
- Repository language is English. CLI output is plain and utilitarian — no
  emojis, no decorative Unicode.

## Stack

Python ≥ 3.12 with uv. Pydantic v2 (schemas), Typer + Rich (CLI), `mcp`
(MCP server), `anthropic` (LLM; research/challenge classes on `claude-fable-5` at effort high
with server-side fallback to `claude-opus-4-8`; cognition/generation on
`claude-opus-5` adaptive thinking at effort high; `claude-haiku-4-5` only for
the lightweight extraction routing class). Tests
with pytest; LLM calls are always behind the `ModelRouter` seam so tests can
run with a fake router — never call the Anthropic SDK directly from stage or
kata code. Optional extras stay optional: `[ui]` (playwright + beautifulsoup4)
for walkthrough/feature tests, `[interview]` (twilio) for remote validation
interviews; core installs and runs without them, degrading honestly.
