# Codebase map

A navigation map for agents working in `src/bokken/`. Each subpackage entry
gives its **responsibility**, the **key seam(s)** to hold, the **invariant(s)**
an agent must not break, and the **top gotcha**. Symbols are named so you can
grep them; when in doubt, `grep -rn <symbol> src/bokken`.

Read [CLAUDE.md](../CLAUDE.md) (the constitution) first, then this map.

## `journal/` — the source of truth

- **Responsibility.** Append-only JSONL event log; all session state is a
  replay-derived projection.
- **Seams.** `schema.py` (`TAXONOMY`, `EXTENSION_KEYS`,
  `_validate_payload_and_invariants` — honesty checked at write time,
  strict-write / tolerant-read); `store.py` (single-writer `fcntl.LOCK_EX`
  append); `replay.py` (`replay()` is a pure fold to `SessionState`);
  `workspace.py` (`session_config`, `BOKKEN_HOME_ENV`); `query.py`
  (`follow()` tails the log).
- **Invariants.** Never mutate or delete a record. Appends are strict and
  validated; reads are tolerant of unknown keys. `SessionState.tokens_spent()`
  sums only `BILLED_TOKEN_KEYS` — the token meter has one definition.
- **Gotcha.** Promoting an `EXTENSION_KEYS` key to a typed field on an existing
  event re-hashes old records and breaks the chain. Extension keys are the only
  no-hash-risk way to add an optional payload key.

## `models/` — the only provider seam

- **Responsibility.** The single place LLMs are invoked; routing, budget,
  rendering, dispatch, attribution.
- **Seams.** `router.py` (`MODELS` registry, `DEFAULT_ROUTING`,
  `resolve_routing`, `ModelRouter.invoke` = budget-check → render → dispatch →
  exactly one `model.called` record); `prompts.py` (`PROMPTS` registry keyed
  `prompt_id -> (version, template)`, `render_prompt`, `CACHE_SPLIT` marker);
  `anthropic`/`openai`/`auto` providers.
- **Invariants.** Stage and kata code never touch a provider SDK — only the
  router. Attribution names the *served* model, not the requested one (a
  server-side fallback must not produce two disagreeing records).
  `EXTRACTION_ONLY` pins `claude-haiku-4-5` to the extraction lane;
  `resolve_routing` rejects impossible model/lane/effort combos at creation.
- **Gotcha.** `CACHE_SPLIT` must sit after the stable corpus and before the
  per-persona/question tail, or the cache prefix stops caching. Bump the
  `PROMPTS` version whenever a template changes — journals pin the version used.

## `panel/` — evidence and grounding

- **Responsibility.** Load and confine the corpus; cast personas; enforce
  citation grounding and governance firewalls.
- **Seams.** `corpus.py` (`FILE_SIZE_CAP` 200k, `CORPUS_SIZE_CAP` 4M,
  `confine_inputs` root confinement, `EVIDENCE_ROLES`, `validate_citation`);
  `casting.py` (`cast_panel(seed=...)` seeded cast, `journal_manifest` before
  content); `grounding.py` (`grounding_health`); `governance.py`
  (`check_firewall`, `freeze_criteria`, `requires_real_validation`).
- **Invariants.** Every input path is confined under the corpus root. Zero
  persona overlap between interview/ideation and test lanes. Criteria freeze
  *before* options are generated. A source `kind` is part of its source id.
- **Gotcha.** `grounding.py` is the backstop: an invalid citation is forced to
  a `CITATION_INVALID` abstention rather than passed through. Span validation
  is inline in `corpus.py` (there is no standalone `validate_span`).

## `orchestrator/` — the loop

- **Responsibility.** The hand-written DT state machine and the run loop.
- **Seams.** `machine.py` (`FORWARD`, `LOOPBACKS`, `can_exit` per-stage exit
  criteria, `CONCEPT_SELECTION_QUESTION`); `runner.py` (the loop; stopping on
  budget + `MAX_ENGINE_ATTEMPTS_PER_STAGE` stall guard; gate policy;
  `_OVERRIDABLE_CONFIG_KEYS` + `KNOWN_BUDGET_KEYS`; `rework_pending`).
- **Invariants.** Gate policy fails **closed** on an unknown/typo'd policy.
  Overrides are limited to budgets (no self-escalation); a typo'd budget key is
  refused, never treated as unlimited. `rework_pending` is discharged only by
  substantive work in the target stage.
- **Gotcha.** A machine-authored `Answer` carries author provenance — machine
  answers are `simulated` and are never human testimony.

## `kata/` — facilitation moves

- **Responsibility.** The facilitator's playbook and its budget accounting.
- **Seams.** `registry.py` (`Kata.evaluate` — executed *and* suppressed moves
  are always journaled; budgets tighten-only; in-pass sequence tracking);
  `moves.py` (`MVP_MOVES`; derive the count with
  `python -c "from bokken.kata.moves import MVP_MOVES; print(len(MVP_MOVES))"`).
- **Invariants.** Budgets only ever tighten within a pass. `timebox_pivot` is a
  novelty-floor stopping rule.
- **Gotcha.** Kata budgets count executions *within the current engine pass* —
  don't assume a global counter.

## `stages/` — the five DT stages

- **Responsibility.** Empathize / Define / Ideate / Prototype / Test, plus code
  exploration.
- **Seams.** `base.py` (`structured()` returns `Attributed | None`; `None`
  means budget exhausted → stop); `empathize.py` / `define.py` / `ideate.py` /
  `prototype.py` / `testing.py` each expose `run(ctx)`; `schemas.py` (Pydantic
  I/O shapes); `exploration.py` (`CODE_CONTEXT_CAP_CHARS` 120k).
- **Invariants.** Ideate's founder-pick prompt must be **resume-stable** — the
  mailbox is keyed by question text; after `FOUNDER_PICK_ATTEMPTS` it falls back
  to an explicitly journaled default. Exploration citations are code-only, the
  founder ratifies the capability map, and the flow is resume-idempotent.
  `walkthrough`/`ui_tests` need the `[ui]` extra and degrade to an abstention —
  never fatal. Web research runs only when the brief allows it.
- **Gotcha.** `structured()` returning `None` is the stop signal — treat `None`
  as "budget hit, stop", not as an error.

## `interview/` — human validation

- **Responsibility.** Consent-gated remote interviews.
- **Seams.** `engine.py` (`ConsentNotGranted` gate before any question,
  `MAX_TURNS`); `channels.py` (`classify_reply`).
- **Invariants.** No question is asked before affirmative journaled consent.
  Real answers are reported as human testimony (not `simulated`).
- **Gotcha.** `classify_reply` grants consent only on a bare affirmative — an
  ambiguous reply does not.

## `dossier/` — the shared read model

- **Responsibility.** Build the analyst-facing model from the journal and
  render it.
- **Seams.** `model.py` (`build_model` — the shared read model; uses
  `payload_as`/`extension`, never raw string keys); `render.py` (`_flat`).
- **Invariants.** Synthetic material carries its `confidence_class` through to
  the model — interpretations chained to simulated material inherit `simulated`.
- **Gotcha.** `render.py`'s `_flat` prevents markdown injection from
  interpolated text — keep interpolated content flattened.

## `handoff/` — the executable spec

- **Responsibility.** Turn a decided run into an OpenSpec package and
  target-specific adapters.
- **Seams.** `generate.py` (`generate_handoff` refuses on a kill/no-concept
  outcome, drops contradicted-assumption requirements); `render.py` (every
  requirement needs a `SHALL` statement plus a `#### Scenario:` with
  `**WHEN**`/`**THEN**` under `## ADDED Requirements`); `emit.py` (`TARGETS` =
  `claude-code`/`cursor`/`codex`); `finalize.py` (`finalize_session`, idempotent).
- **Invariants.** `finalize_session` runs dossier → handoff → report and only
  generates what does not exist yet. `render.py`'s validator rejects a
  requirement missing SHALL, a scenario, or WHEN/THEN.
- **Gotcha.** Handoff emits **ADDED** requirements. If you hand-author an
  OpenSpec *delta* with `## MODIFIED Requirements`, you must copy the unchanged
  scenarios into it — the tooling replaces, it does not merge.

## `report/` — deliverables

- **Responsibility.** HTML report and PPTX deck.
- **Seams.** `context.py` (`call_cost_usd` — the pricing function, prices the
  *served* model); `page.py` (`_e` HTML escaper, plus `</` → `<\/` before
  embedding in `<script>`); `deck.py` (PPTX).
- **Invariants.** `call_cost_usd` is the single pricing definition. Themes are
  chrome-only, never content.
- **Gotcha.** Anything embedded in a `<script>` block must go through the
  `</`→`<\/` step in addition to `_e`, or it can break out of the script.

## `cli/`, `mcp/`, `demo/`, and top-level shapes

- **`cli/`.** `wiring.py` (`build_runner` = engine assembly;
  `session_router_factory` keeps a demo run on `DemoProvider` across resumes);
  `app.py` (verbs decorated `@guarded`; `autopilot`, `doctor`). Doctor's env
  checks never print secrets.
- **`mcp/`.** `server.py` exposes the tools (derive the count with
  `grep -c '@mcp.tool' src/bokken/mcp/server.py`); `_client_actor` comes from
  the handshake, `MailboxPort` carries founder input, client paths are confined.
- **`demo/`.** `provider.py` is a scripted, deterministic, zero-network
  provider; `USAGE_BY_CLASS` gives a realistic token profile so cost surfaces
  have shape while the receipt still says $0.00.
- **`contract.py`** (top-level `src/bokken/contract.py`) — the shared result
  shapes for the CLI `--json` output *and* MCP tool results (`StatusResult`,
  `RunOutcome`, `HandoffResult`, …). One contract, two surfaces.
- **`library.py`** (top-level) — cross-run learnings; borrowed learnings are
  never laundered into fresh evidence.
- **`bundle.py`** (top-level) — `pack_session` produces one portable archive
  with an honest sha256 manifest.
- **`diffing.py`** (top-level) — `diff_sessions` builds the cross-run diff of
  two finalized runs of the same product (opportunity re-rank, assumption flips,
  capability changes, verdict change). Pure derivation; each delta carries the
  *source record's* confidence class, never a blanket run label; raises
  `DiffRefused` (CLI exit 2) on an unfinalized session or a product mismatch.
- **`backlog.py`** (top-level) — `build_backlog` ranks the assumption register
  and research debt on the impact x uncertainty product (`_priority`); `to_csv`
  / `to_markdown` export it. Pure derivation.
- **`estimate.py`** (top-level) — models a run's cost + token range and per-lane
  breakdown from a brief, before any session exists. Pure derivation: no
  session, no model call, no network, no journal — an illustrative profile, not
  a measurement.

## Where does X live

Line numbers approximate; grep the symbol if it drifted.

| X | Symbol | File |
| --- | --- | --- |
| Event taxonomy + optional keys | `TAXONOMY`, `EXTENSION_KEYS` | `src/bokken/journal/schema.py` |
| Write-time honesty checks | `_validate_payload_and_invariants` | `src/bokken/journal/schema.py` |
| Single-writer append | `append` (`fcntl.LOCK_EX`) | `src/bokken/journal/store.py` |
| State from journal | `replay`, `_apply` | `src/bokken/journal/replay.py` |
| Token meter | `BILLED_TOKEN_KEYS`, `tokens_spent` | `src/bokken/journal/replay.py` |
| The only LLM seam | `ModelRouter.invoke` | `src/bokken/models/router.py` |
| Routing validity | `resolve_routing`, `DEFAULT_ROUTING`, `MODELS` | `src/bokken/models/router.py` |
| Prompt registry + cache marker | `PROMPTS`, `render_prompt`, `CACHE_SPLIT` | `src/bokken/models/prompts.py` |
| Corpus caps + confinement | `FILE_SIZE_CAP`, `CORPUS_SIZE_CAP`, `confine_inputs` | `src/bokken/panel/corpus.py` |
| Citation backstop | `grounding_health`, `CITATION_INVALID` | `src/bokken/panel/grounding.py` |
| Governance firewall | `check_firewall`, `freeze_criteria` | `src/bokken/panel/governance.py` |
| State machine | `FORWARD`, `LOOPBACKS`, `can_exit` | `src/bokken/orchestrator/machine.py` |
| Run loop + stopping rules | `MAX_ENGINE_ATTEMPTS_PER_STAGE`, `KNOWN_BUDGET_KEYS` | `src/bokken/orchestrator/runner.py` |
| Facilitation moves | `MVP_MOVES`, `Kata.evaluate` | `src/bokken/kata/moves.py`, `registry.py` |
| Stage base contract | `structured` | `src/bokken/stages/base.py` |
| Founder-pick resume | `FOUNDER_PICK_ATTEMPTS` | `src/bokken/stages/ideate.py` |
| Code exploration cap | `CODE_CONTEXT_CAP_CHARS` | `src/bokken/stages/exploration.py` |
| Consent gate | `ConsentNotGranted`, `MAX_TURNS` | `src/bokken/interview/engine.py` |
| Shared read model | `build_model` | `src/bokken/dossier/model.py` |
| Spec rendering rules | `SHALL` + `Scenario`/`WHEN`/`THEN` | `src/bokken/handoff/render.py` |
| Adapter targets | `TARGETS` | `src/bokken/handoff/emit.py` |
| Finalization order | `finalize_session` | `src/bokken/handoff/finalize.py` |
| Pricing function | `call_cost_usd` | `src/bokken/report/context.py` |
| HTML/script escaping | `_e` | `src/bokken/report/page.py` |
| Shared CLI/MCP shapes | `StatusResult`, `RunOutcome` | `src/bokken/contract.py` |
| Demo provider profile | `USAGE_BY_CLASS` | `src/bokken/demo/provider.py` |
| MCP tools + mailbox | `_client_actor`, `MailboxPort` | `src/bokken/mcp/server.py` |
| Cross-run learnings | (module) | `src/bokken/library.py` |
| Session archive | `pack_session` | `src/bokken/bundle.py` |
| Cross-run diff | `diff_sessions`, `DiffRefused` | `src/bokken/diffing.py` |
| Validation backlog | `build_backlog`, `_priority` | `src/bokken/backlog.py` |
| Pre-flight estimate | (module) | `src/bokken/estimate.py` |
| Segment x outcome matrix | `build_opportunity_matrix`, `LOW_CONFIDENCE_N` | `src/bokken/report/context.py` |

## Reading order for a new agent

1. `CLAUDE.md` — the constitution.
2. `src/bokken/journal/schema.py` — the event taxonomy and honesty checks.
3. `src/bokken/journal/replay.py` — how state is derived (pure fold).
4. `src/bokken/orchestrator/machine.py` — the stages and their exits.
5. `src/bokken/orchestrator/runner.py` — the loop and stopping rules.
6. `src/bokken/models/router.py` — the single LLM seam.
