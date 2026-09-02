# The Journal: event reference (schema v1)

The Journal is Bokken's single source of truth: an append-only JSONL file per
session (`journal.jsonl`), one JSON object per line, hash-chained and never
mutated. Session state is always a deterministic fold (replay) over it.
Corrections are new events that reference the corrected event — history is
never rewritten.

## Envelope

Every record carries the same envelope:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | string | `"1"` for this taxonomy |
| `seq` | int | session-monotonic, starts at 1, no gaps — the authoritative order |
| `id` | string | globally unique; the target of all `refs` |
| `ts` | string | UTC ISO-8601 timestamp (aware; non-UTC is rejected) |
| `session_id` | string | the session slug |
| `type` | string | dot-namespaced event type from the taxonomy below |
| `stage` | string\|null | `intake · empathize · define · ideate · prototype · test · complete`, or null for stage-independent events |
| `actor` | object | `{kind: human\|agent\|system, name, model?, persona_id?}` |
| `payload` | object | type-specific (validated against the taxonomy; unknown fields tolerated on read) |
| `refs` | string[] | event ids this event derives from or responds to |
| `prev_hash` | string | the previous record's `hash` (`"0"×64` genesis for seq 1) |
| `hash` | string | SHA-256 over the record's canonical JSON (sorted keys, minus `hash`) |

**Integrity**: `verify_chain` checks seq contiguity, `prev_hash` linkage, and
per-record hashes; tampering reports the first broken `seq`. Appends are
fsync-durable and line-atomic; a single-writer `flock` prevents interleaving.

**Confidence classes** (`observed | reported | assumed | simulated`) mark the
epistemic status of evidence and propagate to everything derived from it.
Invariants enforced at the append boundary: persona evidence must be
`simulated`; human evidence can never be `simulated`.

## Taxonomy

### `session.*` — lifecycle

| Type | Payload | Notes |
| --- | --- | --- |
| `session.created` | `name, mode (founder\|dojo), brief, config` | the brief includes typed `inputs` (repo/metrics/discussions/documents); `config` snapshots gate policy, budgets, panel, routing |
| `session.resumed` | `config_overrides?` | every run continuation; overrides are human-only and limited to `budgets` |
| `session.gate_requested` | `gate_id, from_stage, to_stage` | the run halts until resolved |
| `session.gate_resolved` | `gate_id, resolution (approve\|reject), reason?` | rejection requires a reason and keeps the stage |
| `session.stopped` | `reason (completed\|budget_exhausted\|novelty_floor\|criteria_met\|human_stop\|error), detail?` | every termination has exactly one enumerated reason |

### `evidence.*` — what entered the record

| Type | Payload | Notes |
| --- | --- | --- |
| `evidence.captured` | `content, source, confidence_class, speaker?, segment?, grounding?, citations[]` | citations carry `source_id`, line span, and `source_kind` (`code · metrics · discussion · document`) |
| `evidence.abstained` | `question, gap, segment?` | research debt: an unanswerable question, never papered over |
| `evidence.input_rejected` | `path, reason` | a declared corpus input the ingestion refused (outside the authorized input root, missing, unsupported suffix, over the size cap) — a grounding gap on the record, not a silent skip |

### `interpretation.*` — what was made of it

| Type | Payload | Notes |
| --- | --- | --- |
| `interpretation.derived` | `kind (insight\|theme\|pov\|hmw\|desired_outcome\|outcome_score\|opportunity), statement, ungrounded; outcome scores carry importance/satisfaction/persona_id, opportunity records carry score/band/per_persona` | `refs` point at supporting evidence or outcome events; empty refs force `ungrounded: true` |

### `option.*` — the idea lineage graph

| Type | Payload | Notes |
| --- | --- | --- |
| `option.created` | `summary` (+ `private_thought`, `visibility` in Dojo) | contributor provenance on the actor |
| `option.built_on` | `summary` | `refs` → parent option (required) |
| `option.merged` | `summary, reason?` | `refs` → merged sources (required); sources become status `merged` |
| `option.split` | `summary, reason?` | `refs` → source option |
| `option.parked` | `reason` | `refs` → parked option |
| `option.killed` | `reason` | `refs` → killed option (required) — why the losers lost is always on record |

### `decision.*` — IBIS decision records

| Type | Payload |
| --- | --- |
| `decision.recorded` | `question, options[], criteria[], positions[{actor, position}], resolution, dissent[{actor, reservation}], requires_real_validation` |

Dissent is first-class: reservations are stored verbatim and surface in the
Dossier. Panel governance also journals its checks as decisions: the frozen
convergence criteria (`question: "convergence criteria"`) and the contamination
firewall verification (`question: "contamination firewall check"`).

### `assumption.*` — the register

| Type | Payload | Notes |
| --- | --- | --- |
| `assumption.registered` | `statement, impact (low\|medium\|high), uncertainty (low\|medium\|high)` | riskiest = highest impact × uncertainty; drives prototype fidelity |
| `assumption.scored` | `score (supported\|contradicted\|untested), rationale?` | `refs` → the assumption + evaluating evidence (required) |

### `facilitation.*` — the Kata inside its own audit scope

| Type | Payload | Notes |
| --- | --- | --- |
| `facilitation.move_executed` | `move_id, trigger, params, outcome` | the rendered move text is the `outcome` |
| `facilitation.move_suppressed` | `move_id, trigger, reason (budget_exhausted\|out_of_stage\|mode_config\|superseded)` | suppressed self-escalation attempts also land here (`move_id: config_change_attempt`) |

### `transition.*` — the loop mechanics

| Type | Payload | Notes |
| --- | --- | --- |
| `transition.fired` | `from_stage, to_stage, condition` | `refs` carry the justification (evidence/decision ids); loop-backs are ordinary transitions on the legal edges `test→define`, `test→empathize`, `define→empathize` |

### `model.*` — every LLM call

| Type | Payload |
| --- | --- |
| `model.called` | `routing_class (research\|challenge\|cognition\|extraction\|generation), model, prompt_id, prompt_version, prompt_hash, request_id?, usage {input/output/cache tokens}, status (ok\|refused\|error\|truncated), duration_ms, web_search` |

Prompt *content* never enters the ledger — the id, version, and content hash
do, so any output is traceable to the exact prompt that produced it, and token
budgets are enforceable from replay.

### `artifact.*` — files on disk, hashes in the ledger

| Type | Payload | Notes |
| --- | --- | --- |
| `artifact.generated` | `path, kind, content_hash` (+ kind-specific extras) | kinds include prototype artifacts (`concept_one_pager`, `landing_copy`, `storyboard`, `demo_script`, `wireframe_html`), `panel_manifest` (with `persona_ids` for the firewall), `opportunity_ranking`, `ui_screenshot`/`ui_review`, `market_research`, `validation_guide`, `wireframe_html`, `dossier_markdown`/`dossier_json`, `handoff_spec`/`handoff_package`, and `report_deck`/`report_page` |

## Reading the ledger

```sh
bokken journal <name> --type option --stage ideate     # the lineage as it happened
bokken journal <name> --type facilitation              # every move, executed or suppressed
bokken journal <name> --since 120 --follow             # tail live from seq 120
bokken journal <name> --since 2026-08-31T18:00:00Z     # or from a timestamp
bokken journal <name> --json | jq 'select(.type=="decision.recorded") | .payload.dissent'
```

Programmatic access mirrors the CLI: `bokken.journal.query(...)` and
`bokken.journal.follow(...)`; state via `bokken.journal.replay_session(dir)`.

## Evolution rules

The taxonomy is versioned. Payloads are read tolerantly (unknown fields are
preserved), so additive payload fields are non-breaking; new event *types* or
envelope changes require a spec delta against the `journal` capability with a
migration note. Records, once written, are never migrated in place.

## Post-completion events

Validation interviews append after `complete`: participant answers are
`evidence.captured` with `actor.kind: human`, `confidence_class: reported`,
and source `validation interview (...)`; rescoring appends
`assumption.scored` with refs to those exchanges. Wireframe exercises journal
observed evidence with source `wireframe_exercise`. The insights library lives
outside the journal (workspace `library.jsonl`) and never masquerades as
session evidence.
