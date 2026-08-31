# Tasks: add-input-sources

## 1. Corpus and brief

- [x] 1.1 Add `kind` to `Source`, implement `Inputs` model on the brief (repo/metrics/discussion/document paths) and `Corpus.ingest_inputs` with the repo allowlist, exclusions, and size cap; verify with a fixture repo (code + junk + oversized file) that only allowlisted files ingest with repo-relative names
- [x] 1.2 Expose `ids_of_kind` and kind-aware `context_for`; verify mixed-inputs addressability with a repo + CSV + transcripts fixture
- [x] 1.3 Embed `source_kind` in citations at evidence-journal time in the Interviewer; verify the metrics-grounded evidence scenario

## 2. Integration

- [x] 2.1 Wire typed inputs through stage engines (empathize grounding scopes, feasibility persona scoped to code+metrics); verify in the stage-engine offline end-to-end test with a fixture repo and metrics file
