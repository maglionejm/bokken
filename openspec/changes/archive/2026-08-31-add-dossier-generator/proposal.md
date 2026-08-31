# Proposal: add-dossier-generator

## Why

The Session Dossier is the deliverable (Blueprint §5.2): within minutes of a run ending, a three-part account — outcomes, process narrative, evidence graph — generated purely from the Journal. It is what makes the ledger legible to stakeholders ("did you consider X?" answered with receipts) and what carries the honesty rules (synthetic labeling, confidence propagation, negative space) to the reader. Without it, the moat is just a log file.

## What Changes

- Introduce the Dossier generator: derive Parts A/B/C from a session journal on demand, at any point in a run (partial dossiers for in-flight sessions are labeled as such).
  - **Part A — Outcomes** (~2 pages): problem statement chosen, concept(s) advanced, prototype + assumption register, test results, decisions with owners and dates, recommended next loop.
  - **Part B — Process narrative**: the arc through the stages with ledger references, pivotal moments, options seriously considered and why the losers lost, dissent and how it was handled, facilitation interventions and effects, loop-backs with triggers.
  - **Part C — Evidence graph**: the full traceable web as machine-readable JSON — insights→evidence, idea lineage, IBIS decision records, persona provenance cards and abstentions, artifact traces, model traces.
- Introduce exports: `dossier.md` (Parts A+B, human-readable) and `dossier.json` (Part C + structured A/B, machine-readable contract for programmatic consumption).
- Introduce the honesty rules as generator invariants: line-level synthetic labeling, confidence-class propagation with validation flags, and the negative-space section (what Bokken did not do).

## Capabilities

### New Capabilities

- `dossier`: Session Dossier generation from the Journal — content contract for Parts A/B/C, exports, and honesty rules.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/dossier/`.
- Depends on: `journal` (sole input), `stages`/`panel` event payloads (read-only).
- Downstream: `cli` (`bokken dossier`) and `mcp` (dossier resource/tool) expose it; the JSON export is a public contract to keep stable.
