# Change: add-session-pack

## Why

Issue #48: a run's outputs are the product's best advertisement, and they do
not travel - sharing a run means hand-tarring a directory whose HTML used to
need a CDN and whose handoff dangles relative references. The bundle makes
the run an object.

## What Changes

- `bokken pack NAME [--deliverables-only] [--out]`: one zip with a
  self-describing manifest (version, dates, verdict, cost, per-file sha256),
  the self-contained report + deck + dossier + handoff tree, and - unless
  deliverables-only - the journal, evidence graph, and artifacts.
  Deliverables-only bundles state their omission in the manifest.
- Refuses unfinalized sessions with a pointer to `bokken export`.

## Impact

- Affected specs: `cli` (ADDED Pack verb requirement)
- Affected code: `bundle.py` (new), `cli/app.py`
