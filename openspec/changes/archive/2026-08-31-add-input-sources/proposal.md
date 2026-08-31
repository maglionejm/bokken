# Proposal: add-input-sources

## Why

A Design Thinking run should start from something tangible, not a blank page. Bokken's key inputs are: (a) an existing app repository the agents can explore, (b) business and performance metrics, and (c) human discussions, interviews, and needs statements — plus generic documents. Today the corpus is an undifferentiated pile of text files; typed inputs let personas and stage engines ground on the product as it actually exists, cite code and metrics with provenance, and let the Dossier state exactly which kind of evidence supports each conclusion.

## What Changes

- Generalize the evidence corpus into typed input sources: `code` (an app repo directory), `metrics` (CSV/JSON business and performance data), `discussion` (interview transcripts, meeting notes, needs statements), and `document` (everything else textual).
- Extend the session brief with a declared `inputs` block (repo path, metrics paths, discussion paths, document paths) journaled at creation like the rest of the brief.
- Repo ingestion rules: source-code files only (documented extension set), size caps, `.git`/vendored/binary exclusion, sources named by repo-relative path.
- Evidence provenance: every corpus-grounded evidence event and citation carries the source kind, so downstream state and the Dossier can distinguish "the code says" from "a user said" from "the metrics show".

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `panel`: ADDED requirement for typed input sources on the corpus (ingestion rules, kind provenance on citations and evidence).

## Impact

- Code: `src/bokken/panel/corpus.py` (typed ingestion), `bokken.journal.schema.Brief` (additive optional `inputs` field), stage engines (ground empathize/define on typed inputs).
- Active changes amended: `add-stage-engines` (grounding scenarios), `add-cli-surface` (input flags on `bokken new`).
