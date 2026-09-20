# Surface the underserved-segment heatmap (ODI/Ulwick core)

## Why

Bokken already computes the Ulwick opportunity ranking — but it collapses
across the panel. The current opportunity view answers *which outcome is most
underserved overall*; it cannot answer the question a founder actually acts on:
**which segment is most underserved on which desired outcome.** That is the
ODI/Ulwick core — the segment-by-outcome opportunity landscape is where an
under-served niche hides behind an average-served market.

The data to answer it already exists in the journal and needs no new model
calls. Every segment persona scores every desired outcome: the Empathize stage
journals per-persona `interpretation.derived` records of kind `outcome_score`
carrying `persona_id`, `importance`, and `satisfaction`, and each persona
carries a `segment`. The Ulwick opportunity score is a deterministic function of
those two numbers (`importance + max(importance - satisfaction, 0)`). So we can
group scores by `(segment, outcome)`, take the mean opportunity score per cell,
and count the personas behind it — a **pure derivation** from replayed events.

Two honesty concerns make this worth specifying carefully rather than bolting
on. First, a cell backed by one persona is not a finding; the sample size must
travel with every number so a thin cell reads as thin. Second, this is still a
simulated run — the heatmap is opinion from synthetic personas, and the
existing simulated-run framing must carry over unchanged.

## What Changes

Add a segment × outcome opportunity matrix as a first-class, derived surface on
two of Bokken's existing consumption channels. No new events, no new model
calls — this reads the journal that Empathize already writes.

- **New CLI verb `bokken opportunities <name>`** — prints a terminal matrix
  (segments as rows, desired outcomes as columns, the mean opportunity score in
  each cell) with the per-cell sample size shown next to every score, and
  `--json` emitting the same data. Cells with `n < 2` are flagged
  low-confidence. For a dojo session the simulated-run framing is stated.
- **New "Underserved by segment" heatmap section in the HTML report** — the
  same matrix rendered as a heatmap, each cell showing its opportunity score and
  its sample size, low-confidence cells visibly flagged, and the dojo
  simulated-run banner honored. The deck carries the corresponding slide.

Both surfaces read one derivation so the CLI number and the report number agree
for a given session, mirroring how `costs` and the report already share one
pricing function.

## Impact

- **Affected specs:** `cli` (ADDED: *Opportunities verb*), `report` (ADDED:
  *Segment opportunity heatmap*).
- **Affected code (for the implementer — this change does not touch `src/`):**
  - `src/bokken/contract.py` — a new `OpportunityMatrix` shape (Pydantic
    `BaseModel` with a `kind` discriminator, consistent with `StatusResult`
    et al.) carrying the segment rows, the outcome columns, and per-cell
    `{score, n, low_confidence}` triples, plus the simulated flag — the one
    shape shared by the CLI `--json` output and the report derivation.
  - `src/bokken/cli/app.py` — a new `@guarded` `opportunities` verb addressing
    the session by name through the core, printing the human matrix and, under
    `--json`, emitting the `OpportunityMatrix` shape via `emit(...)`.
  - `src/bokken/report/context.py` — derives the `OpportunityMatrix` from the
    replayed `outcome_score` interpretations grouped by `(segment, outcome)`
    (mean opportunity score + n per cell), reusing the existing opportunity
    scoring so the report and the verb agree; sessions with no scored outcomes
    omit the section honestly.
  - `src/bokken/report/page.py` — renders the "Underserved by segment" heatmap
    section (score + sample size per cell, low-confidence flag, no-script
    fallback), and `src/bokken/report/deck.py` renders the matching slide.
- **Honesty invariants preserved:** no model calls (pure derivation from the
  journal); per-cell sample size always shown; `n < 2` cells flagged
  low-confidence on both surfaces; the dojo simulated-run banner is carried over
  and never dropped by the heatmap section.
- **No new dependencies.** Deterministic, offline, replay-derived.
