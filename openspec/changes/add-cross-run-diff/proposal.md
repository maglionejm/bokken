# Proposal: add-cross-run-diff

## Why

A product is rarely decided in one run. A founder runs Bokken on a repo,
gets a `kill`, changes the product, and runs it again; or a second run adds
interview evidence that flips an assumption. Today the two runs sit in the
journal as separate sessions and the library (`bokken library`) shows a flat
list of learnings — but nothing answers the question that actually drives the
next decision: *what moved between these two runs of the same product?*

The pieces to answer it already exist. `dossier/model.py`'s `build_model`
derives a typed, honesty-labelled read model from the journal alone — no model
calls — carrying exactly the four things that move run-to-run: the Ulwick
opportunity ranking (insights with `kind == "opportunity"`, `score`, `band`),
the assumptions with their `supported | contradicted | untested` score, the
code-exploration `current_capability` insights, and the recommendation verdict
(the "kill, iterate, or proceed" decision). A diff is therefore pure
derivation: build the model for each finalized session and compare. This keeps
Blueprint §honesty intact — no synthesis, no LLM, so no laundering risk — and
stays offline and deterministic like the rest of the read surface.

## What Changes

- Add `bokken diff <old> <new>` — a read verb that compares two finalized runs
  of the *same product* and reports what moved, derivation only (no model
  calls). It builds the dossier model for each session and diffs four axes:
  1. **Opportunity re-ranking.** Outcomes present in both runs (matched by
     statement), with score and band deltas; outcomes added in `<new>`;
     outcomes dropped from `<old>`.
  2. **Assumptions that flipped status.** Matched by statement text, reporting
     the `<old>` score and the `<new>` score when they differ (e.g.
     `untested -> supported`, `supported -> contradicted`), plus assumptions
     added or dropped.
  3. **Current capabilities added / removed / changed.** The
     `current_capability` insights, matched by statement.
  4. **Verdict change.** The recommendation (`kill | iterate | proceed`) in
     each run, and whether it changed.
- **Honesty is spec-level, not cosmetic.** Every reported row labels which run
  it came from (`old` / `new` / `both`) and carries the confidence class of
  the material it summarizes (an opportunity grounded only in `simulated`
  material stays `simulated` in the diff; an assumption backed by real testing
  reads as such). The diff never re-derives or re-grounds anything — it copies
  the labels the two models already carry.
- **Fail-closed refusals.** The verb SHALL refuse with exit code `2` (never a
  silent empty diff) when either session is unfinalized, or when the two
  sessions are not the same product — comparing the library product key
  (`inputs.repo` or, absent that, the brief `problem_space`). A refusal names
  which precondition failed and which session failed it.
- **Two surfaces, one shape.** A terminal table by default; `--json` emits a
  single `DiffResult` document. Both are produced from the same derived
  structure so they never disagree, matching the `contract.py` discipline used
  by every other read verb.
- A combined cross-run **HTML** report is explicitly **out of scope for v1** —
  CLI table plus `--json` only.

## Capabilities

### New Capabilities

(none — this extends the existing `cli` capability with one verb)

### Modified Capabilities

- `cli`: adds the `diff` verb (a read verb with `--json`, exit-code
  discipline, and honesty labelling consistent with the existing surface).

## Impact

Code seams the implementer will touch (spec-writer does not touch `src/`):

- **`src/bokken/diffing.py`** (new) — the pure derivation helper. Takes two
  `session_dir` paths, calls `dossier.model.build_model` on each, checks the
  finalized + same-product preconditions (reusing `library._product_key`
  semantics for product identity), and returns the diff data structure with
  per-row run provenance and confidence classes. No model calls, no journal
  writes, no session mutation. Alternatively this may live under `dossier/`;
  either way it is one derivation module that both surfaces consume.
- **`src/bokken/contract.py`** — add a `DiffResult` shape (with nested row
  shapes for opportunity deltas, assumption flips, capability changes, and the
  verdict change) so the CLI `--json` output has a documented, stable contract,
  consistent with `StatusResult` / `HandoffResult` / `ExportResult`.
- **`src/bokken/cli/app.py`** — add the `@guarded @app.command("diff")` verb:
  resolve both session dirs, call the derivation helper, map its refusal to
  exit `2` via `_fail`, render the table (plain utilitarian English, no emojis)
  or print the `DiffResult` JSON under `--json`.

No changes to the journal schema, the router, or any external seam. No new
runtime dependency (stdlib + Pydantic v2, already present). The MCP surface is
untouched in v1; `DiffResult` lives in the shared `contract.py` so an MCP tool
could adopt it later without a reshape.
