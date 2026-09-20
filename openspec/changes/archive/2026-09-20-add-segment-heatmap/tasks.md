# Tasks — add-segment-heatmap

## 1. Contract shape

- [x] 1.1 Add an `OpportunityMatrix` shape to `src/bokken/contract.py`: a
  Pydantic `BaseModel` with a `kind` discriminator (consistent with
  `StatusResult` et al.), carrying the ordered `segments`, the ordered
  `outcomes`, per-cell `{score, n, low_confidence}` triples keyed by
  `(segment, outcome)`, and a `simulated` flag. One shape shared by the CLI
  `--json` output and the report derivation.

## 2. Derivation (report context)

- [x] 2.1 In `src/bokken/report/context.py`, derive the `OpportunityMatrix`
  from the replayed `interpretation.derived` records of kind `outcome_score`:
  resolve each record's `persona_id` to its persona's `segment`, group by
  `(segment, outcome)`, compute the mean Ulwick opportunity score
  (`importance + max(importance - satisfaction, 0)`) and the sample size `n`
  per cell, and mark `low_confidence` when `n < 2`. Reuse the existing
  opportunity scoring so the report and the verb agree.
- [x] 2.2 Carry the session's simulated flag onto the matrix. Return an empty /
  omitted matrix when no outcomes were scored.

## 3. CLI verb

- [x] 3.1 Add a `@guarded` `bokken opportunities <name>` verb to
  `src/bokken/cli/app.py`: resolve the session by name through the core, build
  the `OpportunityMatrix`, print the human-readable segment × outcome matrix
  with per-cell score and sample size (low-confidence cells flagged, dojo
  framing stated), and emit the shape under `--json` via `emit(...)`.
- [x] 3.2 Exit 2 with a specific message when the session has no scored
  outcomes; unknown session exits 2 per the existing output discipline.

## 4. Report rendering

- [x] 4.1 In `src/bokken/report/page.py`, render the "Underserved by segment"
  heatmap section from the matrix: cell score + sample size, low-confidence
  flag, and a no-script fallback listing the same numbers. Omit when there is
  no matrix; keep the dojo simulated framing.
- [x] 4.2 In `src/bokken/report/deck.py`, add the matching slide.

## 5. Tests and verification

- [x] 5.1 Tests: matrix computed with per-cell sample sizes; an `n<2` cell
  flagged low-confidence on both surfaces; dojo framing preserved; no-outcomes
  session refused (CLI exit 2) and section omitted (report); CLI number equals
  report derivation for the same session; no `model.called` events added by
  either surface.
- [x] 5.2 `make check` green (ruff + pytest + `openspec validate --strict`).
