# Design: add-input-sources

## Context

See proposal.md. The corpus (panel capability, already implemented) is line-addressable text with content-hash source ids; the Brief payload model tolerates additive fields (journal tolerant-reader rule). This change generalizes ingestion without touching citation mechanics.

## Goals / Non-Goals

**Goals:**

- One `inputs` declaration on the brief; one typed ingestion path; kind provenance end-to-end (source → citation → evidence event → state → dossier).
- Repo ingestion that is safe by default (no binaries, no `.git`, size caps) and useful to personas (repo-relative names).

**Non-Goals:**

- Code *execution* or static analysis of the repo (agents read code as text in MVP).
- Metrics computation/aggregation — metrics files are citable evidence, not a query engine.
- Live integrations (analytics APIs, call recorders) — file-based inputs only for MVP.

## Decisions

1. **`Source` gains a `kind` field; `Corpus.ingest_inputs(inputs)` supersedes bare path ingestion** — kinds resolved from the brief's `inputs` block, not guessed from extensions (except within a repo, where the extension allowlist filters files).
2. **Repo allowlist, not denylist** — a documented set of source/config extensions (`.py`, `.ts`, `.js`, `.tsx`, `.go`, `.rs`, `.java`, `.rb`, `.md`, `.toml`, `.yaml`, `.yml`, `.json`, `.sql`, `.html`, `.css` …) plus a 200 KB per-file cap; `.git`, `node_modules`, `.venv`, `dist`, `build` excluded. Alternative: gitignore parsing — heavier, deferred.
3. **`source_kind` rides on citations at journal time** — the Interviewer resolves each citation's kind from the corpus and embeds it in the evidence payload (payloads are extra-tolerant), so replay/dossier need no corpus access.
4. **Grounding scopes can select by kind** — `Persona.grounding_scope` keeps source ids, and `Corpus.ids_of_kind(kind)` lets casting scope role agents (feasibility → `code` + `metrics`).
5. **Brief.inputs is optional and additive** — sessions without tangible inputs still run (blank-page founder mode stays legal).

## Risks / Trade-offs

- [Large repos overflow persona context] → per-file size cap + scoped grounding; retrieval upgrades stay a later change.
- [CSV metrics cited by line are awkward] → acceptable: line spans still resolve; a metrics query engine is out of scope.

## Open Questions

- None blocking.
