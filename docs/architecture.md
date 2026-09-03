# Architecture

Bokken is a small set of layers around one invariant: **the Journal is the only
source of truth**. Every layer either appends events to it or derives views from
it. Session state is never held anywhere else — replaying the ledger *is* the
state, which is what makes every run crash-safe and resumable by construction.

```
                    consumers (human terminal / agents & IDEs)
                          │                     │
             ┌────────────┴─────┐   ┌───────────┴────────────┐
  SURFACES   │  CLI (typer)     │   │  MCP server (stdio)    │   src/bokken/cli
             │  new run step .. │   │  12 tools, 4 resources │   src/bokken/mcp
             └────────┬─────────┘   └───────────┬────────────┘
                      └────────┬────────────────┘
                               │  shared result shapes: src/bokken/contract.py
             ┌─────────────────┴──────────────────────────────┐
  CORE       │  ORCHESTRATOR   src/bokken/orchestrator        │
             │  stage machine (intake→empathize→define→ideate │
             │  →prototype→test→complete + loop-backs),       │
             │  runner (create/run/step/stop), exit criteria, │
             │  human gates, budgets, stopping rules,         │
             │  no-self-escalation guard                      │
             ├──────────────┬─────────────┬───────────────────┤
             │ STAGE ENGINES│    KATA     │      PANEL        │
             │ src/…/stages │ src/…/kata  │  src/…/panel      │
             │ the five DT  │ 9 named,    │  persona casting, │
             │ stage        │ budgeted    │  typed corpus     │
             │ behaviors    │ moves, all  │  (code/metrics/   │
             │ (both modes) │ journaled   │  discussion/doc), │
             │              │             │  grounding+abstain│
             │              │             │  firewall, anti-  │
             │              │             │  sycophancy       │
             ├──────────────┴─────────────┴───────────────────┤
  MODEL OPS  │  MODEL ROUTER   src/bokken/models              │
             │  routing classes → models (research/challenge →│
             │  claude-fable-5 high, cognition/generation →   │
             │  claude-opus-5 high, extraction → claude-haiku-  │
             │  4-5), budget pre-check, structured outputs,   │
             │  versioned prompts, every call → model.called  │
             │  └── AnthropicProvider (SDK; swappable seam)   │
             ├────────────────────────────────────────────────┤
  LEDGER     │  JOURNAL   src/bokken/journal                  │
             │  event schema v1 (10 families, 22 types),      │
             │  append-only JSONL + SHA-256 hash chain,       │
             │  single-writer lock, replay → SessionState,    │
             │  queries + follow                              │
             ├────────────────┬───────────────────────────────┤
  OUTPUTS    │  DOSSIER       │  HANDOFF                      │
             │  src/…/dossier │  src/bokken/handoff           │
             │  journal →     │  journal → SpecPackage →      │
             │  DossierModel →│  OpenSpec change package      │
             │  dossier.md    │  (proposal/design/specs/tasks │
             │  (A+B) +       │  + traceability.json), format-│
             │  dossier.json  │  validated; contradicted      │
             │  (C, versioned │  assumptions → exclusions;    │
             │  contract)     │  validation debt → tasks      │
             └────────────────┴───────────────────────────────┘
                               │
  DISK       .bokken/sessions/<slug>/
             ├── journal.jsonl          the ledger (source of truth)
             ├── .lock                  single-writer guard
             ├── artifacts/             prototypes, panel manifests
             ├── dossier/               dossier.md + dossier.json
             ├── handoff/               OpenSpec MVP specs + traceability.json
             ├── report/                report.pptx + report.html (journal-derived)
             ├── artifacts/validation/  validation_guide.md (+ real-interview evidence in the ledger)
             └── pending_question.json / answers.json  (MCP input mailbox)
```

## The loop at runtime

1. A **surface** (CLI or MCP) resolves the session by name and builds a
   `Runner` with the engines, an input port, and the Kata.
2. The **runner** replays the journal, then loops: check completion → pending
   gate → stop → budgets → gate approvals → stage **exit criteria**. If the
   criteria are met it fires a journaled `transition.fired` (with justification
   refs); if not, it invokes the stage **engine**.
3. **Engines** do the stage's work through three seams only: the **input port**
   (human answers in Founder mode; halts as `input_pending` when headless), the
   **panel** (synthetic participants in Dojo mode), and the **model router**
   (all LLM calls). Everything they produce is a journal event.
4. The run returns at the next **halt** (`completed | gate_pending |
   input_pending | stopped`); no call is unbounded. Resolving a gate or
   submitting an answer is itself an append, so any process — or any MCP
   client — can continue the run later.
5. The **dossier** generator derives Parts A/B/C from the ledger alone, at any
   point (partial dossiers are labeled).
6. On completion, the surfaces **finalize** the run: Dossier, then the
   **handoff** — one journaled model call drafts an OpenSpec spec package for
   the validated concept, deterministic renderers and a structural validator
   guarantee the format, and honesty carries over in code (contradicted
   assumptions become exclusions, validation debt becomes mandatory tasks).
   Finalization ends with the **report** exports — the run as a PPTX deck
   and a self-contained HTML page, both deterministic renderings of the
   Journal with a one-line-per-spec appendix. Finalization is idempotent;
   the handoff (only) is skipped for `kill` recommendations.

## Design invariants

- **Journal first**: no side state; corrections are new events; records are
  hash-chained and never mutated.
- **Mode parity**: Founder and Dojo execute the same machine, criteria, gates,
  and schema — they differ only in who supplies participation.
- **Governance in code, not prompts**: gates, budgets, stopping rules,
  contamination firewall, criteria freeze, skeptic quota, synthetic labeling,
  and the self-escalation guard are all enforced by code paths with journaled
  outcomes.
- **Market frameworks in the engines**: Empathize derives JTBD desired
  outcomes and journals a deterministic Ulwick opportunity ranking; Ideate
  converges through three firewalled lenses (adversarial feasibility against
  the repo with green/amber/red verdicts and veto, independent RICE with no
  code access, outcome desirability); concept one-pagers are Hills
  (Who/What/Wow) with a Lean-UX hypothesis; `wireframe_html` prototypes are
  built on the repo's real CSS tokens and exercised in a browser; a declared `app_url` adds a
  documented functional UI walkthrough as observed evidence.
- **Concept research on the record**: after the concept decision, an
  explicitly authorized (`allow_web_research: true`) research-class call with
  server-side web search produces a structured market record - competitors
  with overlap, sourced signals, regulatory, risks - journaled as `reported`
  evidence and fed to the assumption register.
- **Validation is a first-class phase**: after completion, `bokken validate`
  derives an interview guide from the research debt, an agentic interviewer
  moderates real humans over a channel port (terminal or Twilio), and the
  register is rescored against `reported` human evidence — appends after
  completion are legal and replay-safe.
- **Memory with provenance**: finalization feeds a workspace-level insights
  library; new runs on the same product are seeded with prior learnings,
  always labeled with the originating session.
- **Fusion lanes (cost architecture)**: a frontier lane (Fable 5 for
  research/challenge, Opus 5 for execution/documentation) and a cheaper
  sidekick lane (Sonnet 5) with parallel per-lane prompt caches. The sidekick
  reads — corpus retrieval as verbatim spans, UI-step selection — so the
  frontier judges; anything feeding a `decision.recorded` never leaves the
  frontier. `bokken costs` reports spend, cache hit-rate, and the share of
  persona turns the grounding backstop had to abstain on, so a cheaper
  delegated read cannot degrade citations invisibly.
- **One model seam**: nothing outside `bokken.models` touches a provider SDK;
  Anthropic and optional OpenAI adapters stay behind the router, and the whole
  harness runs offline against a fake provider in tests.
- **Deliverables are objects**: `bundle.py` packs a finalized session into
  one archive with a self-describing manifest; `report/theme.py` brands the
  chrome without touching content; `handoff/emit.py` renders the OpenSpec
  package as target-native execution prompts. All three are pure functions
  of the session directory — no model calls, nothing mutated.
- **Two surfaces, one contract**: CLI `--json` output and MCP tool results are
  the same pydantic shapes (`bokken/contract.py`). Trust differs at the edge,
  not in the core: client-supplied input paths are confined to authorized
  roots on the MCP surface, and mailbox answers carry the client's handshake
  identity — a human operating the CLI on their own machine keeps their own
  authority.

## Blueprint mapping

| Blueprint layer (§7) | MVP implementation |
| --- | --- |
| L6 Governance plane | gates, budgets/stopping, self-escalation guard, panel governance |
| L5 The Journal | `bokken.journal` (+ `bokken.dossier`, `bokken.handoff`, `bokken.report` for the derived deliverables) |
| L4 DT Orchestrator | `bokken.orchestrator` + `bokken.stages` + Dojo panel |
| L3 The Facilitator | `bokken.kata` (moves as prompts/injections; no realtime loop yet) |
| L2 Voice & perception | out of MVP scope (input ports instead of ASR/TTS) |
| L1 Surfaces I/O | CLI + MCP (meeting platforms are a later horizon) |
