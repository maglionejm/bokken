# Proposal: add-validation-backlog

## Why

Every dojo run ends flagged `requires_real_validation`, and both the untested
assumptions and the research debt (abstentions) die as scattered facts a
founder has to reconstruct by eye from the dossier. `bokken status` counts
them (`research_debt`, `assumptions_scored`) but never turns them into a
prioritized, exportable to-do list. Teams want the one artifact that answers
"what do I go test next, and in what order" — a ranked validation backlog they
can drop straight into an issue tracker. It is pure derivation from the
journal: no model call is needed, so it can be honest, deterministic, and free.

## What Changes

- New verb `bokken backlog <name>`: a deterministic, replay-derived,
  no-model-call report that ranks the session's untested and contradicted
  assumptions by impact x uncertainty and folds open research debt
  (abstentions) in as backlog items. Confirmed journaled fields:
  `AssumptionRegistered.impact`/`.uncertainty` and `AssumptionScored.score`
  (`journal/schema.py`), surfaced through `dossier/model.py`
  (`AssumptionNode`, `AbstentionNode`).
- Default output is a terminal table (rank, kind, impact, uncertainty,
  confidence class, source, statement). `--json` emits one `BacklogResult`
  JSON document; `--format csv` and `--format markdown` emit a checklist ready
  for an issue tracker.
- A "what would flip the verdict" line derived from the register versus the
  test recommendation thresholds (`stages/testing.py`). The recommendation is
  a challenge-class judgement over the register text, not a mechanical
  threshold, so the backlog does not invent a rule: it states the register
  counts (supported / contradicted / untested) and the gap plainly — how many
  untested items would have to resolve, and that any contradicted item is a
  standing kill/iterate signal — rather than asserting a derived cutoff.
- Honesty: every backlog item carries its `confidence_class` and its session
  provenance; an all-simulated session keeps the simulated framing (the dojo
  banner and `requires_real_validation` context are restated on the backlog so
  a simulated-only backlog is never read as validated fact).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli`: backlog verb.

## Impact

- `src/bokken/cli/app.py` — new `backlog` verb (`@guarded`), with `--json`,
  `--format csv|markdown`.
- `src/bokken/contract.py` — new `BacklogResult` (and item shape) shared by
  the CLI `--json` output; one contract, both surfaces.
- `src/bokken/backlog.py` (new) — the derivation helper: ranks assumptions by
  impact x uncertainty, folds in research debt, computes the flip-the-verdict
  line, and renders csv/markdown. No provider seam is touched.
- tests (implementer, not this package).
