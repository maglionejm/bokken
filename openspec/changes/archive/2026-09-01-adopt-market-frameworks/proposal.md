# Proposal: adopt-market-frameworks

## Why

Live-run outputs were judged low quality: insights were vague, convergence
was generic scoring, and nothing was quantified. The reference workshop that
produced the Vatios "Next 5" deliverable ran a market-proven hybrid — JTBD
desired-outcome scoring (Ulwick opportunity ranking), work-alone divergence
tied to outcome IDs, two firewalled convergence lenses (adversarial
feasibility review against the real codebase; independent RICE scoring with
no code access), and winners written as Hills with Lean-UX hypotheses. Bokken
adopts those mechanics, plus an output-quality contract: every model-facing
prompt demands self-explanatory, quantified, constructive founder-facing
writing.

## What Changes

- Empathize (dojo): after interviews, derive desired-outcome statements
  (JTBD) grounded in evidence; each interview persona scores every outcome
  Importance/Satisfaction 1-10 with reasons for extremes; the facilitator
  computes Opportunity = I + max(I-S, 0) deterministically, journals
  per-outcome opportunity records with bands (>=15 severely underserved,
  12-15 underserved, <10 served) and consensus-vs-segment-spike reading, and
  writes an `opportunity_ranking` artifact.
- Define: clustering and candidate drafting consume the opportunity ranking;
  problem statements must name the segment, the underserved outcomes, and
  the numbers behind them; selection criteria include opportunity coverage.
- Ideate: divergence ties every idea to the outcome(s) it serves; the
  convergence role lenses become framework lenses — the feasibility voter
  runs an adversarial review against the repo corpus (verdict green/amber/
  red with a "first honest slice" and S/M/L effort), the viability voter
  scores RICE without code access, the segment voter scores desirability
  against the outcome ranking. A red feasibility verdict is a veto recorded
  as dissent.
- Prototype: the concept one-pager artifact opens as a Hill (Who / What /
  Wow) plus a Lean-UX hypothesis ("We believe ... measured by ...").
- Output-quality contract on all prompts: constructive, founder-facing,
  self-explanatory, quantified wherever the corpus provides numbers.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Empathize, Define, Ideate, Prototype, and Test engine
  requirements upgraded with the framework mechanics.

## Impact

`src/bokken/models/prompts.py` (v2/v3 bumps), `src/bokken/stages/{schemas,
empathize,define,ideate,prototype,testing}.py`, fake provider handlers,
report/dossier surfacing of the opportunity ranking.
