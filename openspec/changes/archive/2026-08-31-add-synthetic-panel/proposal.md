# Proposal: add-synthetic-panel

## Why

The Dojo (Blueprint §6) runs the identical DT loop with no humans by swapping the human panel for a governed synthetic one. This is explicitly a simulation whose outputs are hypotheses to be validated, not findings — so the panel engine must enforce grounding with abstention, anti-sycophancy structure, and a contamination firewall in code. It also serves Founder mode: synthetic interview panels (clearly labeled) before real users exist. The panel engine is kept separate from facilitation cognition (Blueprint §7.1) — the Test firewall depends on that separation.

## What Changes

- Introduce persona casting from the session brief: sampled demographic/psychographic coverage, OCEAN-style personality variance, plus mandatory role agents — a skeptic with a protected quota, a feasibility engineer, and a viability/CFO voice.
- Introduce evidence-corpus binding: personas answer only from ingested corpus material (files/directories declared in the brief) with span-level citation, or abstain — abstentions are journaled as research debt.
- Introduce the contamination firewall: Test-stage panels are freshly cast and provably disjoint from panels that ideated.
- Introduce anti-sycophancy guarantees: personas never see the sponsor's preferred answer; convergence criteria are fixed and journaled before ideation begins.
- Introduce panel provenance: every persona's casting parameters, grounding sources, and every answer's citation/abstention recorded in the Journal (persona provenance cards).

## Capabilities

### New Capabilities

- `panel`: the governed synthetic persona engine — casting, grounding with abstention, contamination firewall, anti-sycophancy structure, and provenance.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/panel/`.
- Depends on: `journal` (provenance events), model routing seam (LLM-backed persona turns arrive with add-stage-engines' model-ops wiring; this change defines behavior and contracts, testable with fake generators).
- Downstream: stage engines consume panels via the `InputPort`/interview interfaces; dossier surfaces provenance cards.
