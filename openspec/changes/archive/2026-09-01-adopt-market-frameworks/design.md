# Design: adopt-market-frameworks

## Framework source

Mechanics are lifted from the Vatios "Next 5" workshop (JTBD-scored Lightning
Sprint): Ulwick opportunity algebra with bands, firewalled two-lens
convergence, red-verdict veto, Hill + hypothesis output format. They map onto
Bokken's existing event families — outcomes and scores are
`interpretation.derived` records (kinds `desired_outcome`, `outcome_score`,
`opportunity`), the ranking is a journaled artifact, lens verdicts live in
the existing vote/decision events — so the journal schema is unchanged.

## Keeping it light

- The opportunity computation is deterministic facilitator code, not a model
  call; only outcome derivation and scoring are model calls (research class).
- Convergence keeps its single vote loop; lenses are prompt-level
  instructions per voter role, with the repo corpus excerpt injected only
  for the feasibility voter (the RICE voter is firewalled by construction —
  its prompt simply never receives code).
- Founder mode keeps its current interview flow; outcome scoring is
  panel-dependent and therefore dojo-only (documented in the spec).

## Output-quality contract

A shared prompt preamble (`QUALITY_CONTRACT`) is prepended to every
reasoning template: write for the founder, be constructive (what to do next,
not just what is wrong), self-explanatory (no internal jargon, expand every
score), and quantified (cite counts, scores, euros, percentages whenever the
corpus provides them). Registered once so every prompt version hash captures
it.
