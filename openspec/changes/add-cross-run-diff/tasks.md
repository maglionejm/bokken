# Tasks: add-cross-run-diff

## 1. Derivation helper

- [ ] 1.1 Add `src/bokken/diffing.py` (a pure derivation module; may alternatively live under `dossier/`). It SHALL build the dossier model for two `session_dir` paths via `dossier.model.build_model`, with no model calls, no journal writes, and no session mutation; verify with a unit test asserting no `model.called` event is appended to either session and both journals are byte-identical before and after.
- [ ] 1.2 Implement the finalized + same-product preconditions: refuse (a typed refusal the CLI maps to exit 2) when either model's stage is not `complete`, or when the two product keys differ. Reuse the library product-key semantics (`inputs.repo` or brief `problem_space`); verify with unit tests for an unfinalized session and for a product mismatch (repo-vs-repo and problem_space-vs-problem_space).
- [ ] 1.3 Implement the opportunity re-ranking diff: match `kind == "opportunity"` insights by statement across the two models; emit both-run rows with `<old>`/`<new>` score and band plus deltas, added rows, and dropped rows. Verify each bucket with a fixture pair where one outcome re-ranks, one is added, and one is dropped.
- [ ] 1.4 Implement the assumption flip diff: match assumptions by statement; emit a flip row only when the score changed (`supported | contradicted | untested`), plus added/dropped rows. Verify an `untested -> supported` flip, an unchanged assumption (no row), and an added assumption.
- [ ] 1.5 Implement the current-capability diff (`kind == "current_capability"` insights matched by statement: added / removed / changed) and the verdict diff (each run's `kill | iterate | proceed` recommendation and whether it changed). Verify a capability added and a verdict `iterate -> proceed`.
- [ ] 1.6 Carry honesty through every row: each row labels its run of origin (`old` / `new` / `both`) and copies the confidence class from the source model without re-deriving or relabelling. Verify a diff over a dojo (simulated) run keeps rows labelled synthetic and a diff over real testimony does not.

## 2. Contract shape

- [ ] 2.1 Add a `DiffResult` Pydantic model to `src/bokken/contract.py` (with nested row shapes for opportunity deltas, assumption flips, capability changes, and the verdict change; a `kind: Literal["diff"]` discriminator like the other results), plus a builder from the derivation output. Verify it round-trips to JSON and back and that every row carries `run` provenance and `confidence_class`.

## 3. CLI verb

- [ ] 3.1 Add `@guarded @app.command("diff")` in `src/bokken/cli/app.py`: resolve both session dirs, call the derivation helper, and on its refusal call `_fail(msg, 2)`. Verify the same-product happy path and both refusals (unfinalized, product mismatch) with `CliRunner`, asserting exit codes and that stdout is empty on refusal.
- [ ] 3.2 Render the default table in plain utilitarian English (no emojis / decorative Unicode), one section per axis, every row showing its run of origin; under `--json` print exactly one `DiffResult` document to stdout and nothing to stderr. Verify the machine-consumption discipline (single JSON doc, empty stderr, exit 0) and that the table contains all four sections.

## 4. Integration and gate

- [ ] 4.1 End-to-end test: build two finalized offline sessions from one product (fake router), diff them, and assert all three spec scenarios hold (real diff content, product-mismatch refusal, unfinalized refusal). Confirm `make check` is green (ruff + pytest + `openspec validate --strict`).
- [ ] 4.2 Docs follow code: note for the docs-auditor that `docs/codebase-map.md` (the `cli/` and `contract.py` / top-level-shapes entries) and any CLI verb reference should gain the `diff` verb; report — do not fix — in the implementer's PR.
