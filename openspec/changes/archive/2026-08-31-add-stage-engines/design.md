# Design: add-stage-engines

## Context

See proposal.md. Constraints: engines implement the orchestrator's `StageEngine` protocol and cannot write transitions themselves; all participation flows through the input port / panel interfaces; all LLM work flows through the `ModelRouter` seam (CLAUDE.md); the journal schema is frozen — engines only emit taxonomy-v1 events.

## Goals / Non-Goals

**Goals:**

- Stage behavior that satisfies the orchestrator's exit criteria by construction (each engine's happy path produces exactly the events the criteria check).
- One provider integration done properly: Anthropic SDK, adaptive thinking, structured outputs, streaming for long generations, refusal handling.
- Deterministic tests for every governance rule using fake routers/generators.

**Non-Goals:**

- App/code generation for prototypes (v0/Lovable-class integration is a later change; MVP artifacts are documents).
- Multi-provider abstraction — the router seam is provider-shaped-neutral, but only Anthropic is implemented.
- Prompt-quality evals harness (Blueprint SPEC-09 full scope) — MVP logs enough (prompt versions, hashes) to build it later.

## Decisions

1. **`ModelRouter` over raw SDK calls everywhere** — a thin class: `invoke(class_, prompt_id, rendered, schema=None, stream=False) -> Outcome`. Implements journaling, budget check, validation. Anthropic specifics: `client.messages.create` / `messages.parse` (pydantic schemas) / `messages.stream` with `.get_final_message()`; `thinking={"type": "adaptive"}` for `cognition`; check `stop_reason` before reading content and surface `refused` as a typed outcome.
2. **Default routing** — `cognition`/`generation` → `claude-opus-4-8`; `extraction` → `claude-haiku-4-5`. Rationale: Blueprint §7.1 prescribes frontier for cognition and cheaper/faster models for signal extraction; the allowlist keeps overrides sane. Model ids are aliases (no date suffixes).
3. **Prompts as versioned package resources** — `src/bokken/prompts/<area>/<name>@vN.md` loaded by id; hash computed on render. Alternative: inline strings — rejected: untraceable and unreviewable.
4. **Engines as plain classes per stage** — `EmpathizeEngine`, `DefineEngine`, ... each composing: router, kata, input port, panel (Dojo), journal appender from `StageContext`. Interview scripts, clustering, roundtable, register-building are private methods with structured-output schemas (pydantic) per step.
5. **Novelty monitoring** — embed-free MVP: `extraction`-class calls classify each new option as `novel_cluster | variation | duplicate` against the running cluster summary; novelty rate = novel/last-N. Cheap, journaled, and replaceable later.
6. **Private vs public persona thoughts** — both journaled; private marked `payload.visibility: private` and excluded from panel-visible renderings and Dossier Part A/B (Part C may include them flagged). Simpler than a second ledger.
7. **Artifacts on disk, hashes in ledger** — `artifacts/<stage>/<name>.md` etc., journaled by path+hash per journal spec (no blobs in events).

## Risks / Trade-offs

- [Opus-everywhere cost on long Dojo runs] → per-class budgets + stopping rules are enforced by the router/orchestrator; routing overrides allow cheaper cognition explicitly per session (user's call, journaled).
- [Structured-output schema drift vs journal payloads] → step schemas live next to engines and map explicitly into taxonomy events; validation failures never write derived events.
- [Novelty classifier noise] → provocation trigger uses a windowed rate with hysteresis; misfires cost one journaled move, not a stage derailment.
- [Anthropic API changes] → SDK pinned with lower bound; refusal/pause_turn handling covered by tests with recorded fake outcomes.

## Open Questions

- None blocking. Real-user test-plan generation (beyond synthetic-first testing) can be added to the Test engine in a follow-up change without schema changes.
