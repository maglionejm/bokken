# Proposal: add-report-exports

## Why

The Dossier is the honest record, but it is a reading document. Stakeholders
consume workshop outcomes as a deck and as a shareable page. After a flow
finishes, Bokken should export the same story in two presentation formats —
a PowerPoint deck and a self-contained HTML page — covering the entire
process, every intermediate output, and the final outputs, with an appendix
that summarizes each generated handoff spec in one sentence and points to the
full file.

## What Changes

- New `report` capability: deterministic, journal-only generation of
  `report/report.pptx` and `report/report.html` from the DossierModel; both
  journaled as artifacts; honesty labels (Dojo banner, synthetic counts,
  validation flags) carried into both formats.
- Finalization generates the report after the Dossier and the handoff
  attempt, so the appendix can reflect either the generated specs or the
  refusal reason.
- New CLI verb `bokken export <name>` regenerates both files on demand.
- New dependency `python-pptx` (see design.md).

## Capabilities

### New Capabilities

- `report`: PPTX + HTML report exports built deterministically from the
  Journal.

### Modified Capabilities

- `handoff`: run finalization also produces the report exports.
- `cli`: new `export` verb.

## Impact

`src/bokken/report/` (new), `src/bokken/handoff/finalize.py`,
`src/bokken/cli/app.py`, `pyproject.toml` (python-pptx), `tests/report/`.
