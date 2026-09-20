# CLI — spec delta

## Purpose

The CLI is Bokken's terminal surface: barista-style lifecycle verbs over named, durable, resumable sessions, exposing the full DT loop as a thin adapter over the shared core with disciplined human and machine output. This delta adds a cross-run diff verb over that same read surface.

## ADDED Requirements

### Requirement: Diff verb

`bokken diff <old> <new>` SHALL compare two finalized runs of the *same product* and report what moved between them, by derivation only — it SHALL build the shared read model for each session (the dossier model built from the journal alone) and diff it, making no model calls, no journal writes, and no mutation of either session. The report SHALL cover four axes: (1) **opportunity re-ranking** — Ulwick outcomes present in both runs matched by statement, each with its `<old>` and `<new>` opportunity score and band and their deltas, plus outcomes added in `<new>` and outcomes dropped from `<old>`; (2) **assumptions that flipped status** — assumptions matched by statement whose score changed, reporting the `<old>` and `<new>` score (drawn from `supported | contradicted | untested`), plus assumptions added and dropped; (3) **current capabilities added / removed / changed** — the code-exploration `current_capability` insights matched by statement; and (4) **verdict change** — the recommendation (`kill | iterate | proceed`) of each run and whether it changed.

Every reported row SHALL label which run it came from (`old`, `new`, or `both`) and SHALL carry the confidence class of the material it summarizes, copied unchanged from the two read models — the diff SHALL NOT re-derive, re-ground, or relabel anything, so material grounded only in `simulated` or `assumed` evidence stays labelled synthetic in the diff and real testimony reads as such. The verb SHALL refuse with exit code `2`, writing a specific message to stderr and no diff to stdout, when either session is not finalized, or when the two sessions are not the same product — product identity being the library product key (`inputs.repo`, or the brief `problem_space` when no repo is set). The default output SHALL be a plain utilitarian terminal table (no emojis, no decorative Unicode); `--json` SHALL emit exactly one JSON document conforming to the documented `DiffResult` shape, carrying the same per-row run provenance and confidence classes as the table. A combined cross-run HTML report is out of scope for this requirement.

#### Scenario: What moved between two runs of one product

- **WHEN** `bokken diff retention-v1 retention-v2 --json` is invoked on two finalized sessions built from the same repository, where the second run re-ranked an opportunity, flipped an assumption from `untested` to `supported`, added a current capability, and changed the verdict from `iterate` to `proceed`
- **THEN** stdout is exactly one `DiffResult` JSON document (stderr empty, exit code 0) whose opportunity section shows the re-ranked outcome with both scores and the delta, whose assumptions section shows the `untested -> supported` flip, whose capabilities section lists the added capability, and whose verdict section reports `iterate -> proceed`, with every row labelled by run of origin and carrying its confidence class

#### Scenario: Different products are refused

- **WHEN** `bokken diff app-alpha app-beta` is invoked on two finalized sessions whose product keys differ (different `inputs.repo`, or different `problem_space` when neither sets a repo)
- **THEN** the command exits `2` with a stderr message naming that the two sessions are not the same product, and writes no diff to stdout

#### Scenario: An unfinalized session is refused

- **WHEN** `bokken diff done-run in-flight-run` is invoked where `in-flight-run` has not reached the `complete` stage
- **THEN** the command exits `2` with a stderr message naming which session is not finalized and pointing to how to finalize it, and writes no diff to stdout
