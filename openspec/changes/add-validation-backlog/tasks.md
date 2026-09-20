# Tasks: add-validation-backlog

## 1. Derivation helper

- [ ] 1.1 `src/bokken/backlog.py`: build the ranked backlog from the dossier
  model / replay alone — rank untested and contradicted assumptions by
  impact x uncertainty, fold research-debt abstentions in as items, carry
  each item's `confidence_class` and session provenance, and compute the
  register counts (supported / contradicted / untested)
- [ ] 1.2 flip-the-verdict line: derived from the register versus the test
  recommendation in `stages/testing.py`; since the recommendation is a
  challenge-class judgement (not a mechanical cutoff), state the counts and
  the gap plainly rather than inventing a threshold
- [ ] 1.3 csv and markdown renderers (issue-tracker checklist) in the helper

## 2. Contract

- [ ] 2.1 `BacklogResult` (and per-item shape) in `src/bokken/contract.py`,
  including the ranked items, register counts, flip-the-verdict text, and
  honesty flags (simulated framing / requires-real-validation)

## 3. Verb

- [ ] 3.1 `bokken backlog <name>` in `src/bokken/cli/app.py` (`@guarded`):
  default terminal table, `--json` (BacklogResult), `--format csv|markdown`;
  exit 2 on unknown session

## 4. Tests

- [ ] 4.1 offline tests: ranked ordering by impact x uncertainty; supported
  assumptions excluded; research debt included; empty backlog; csv/markdown
  export shape; simulated framing preserved; unknown-session exit 2
- [ ] 4.2 `make check` green (ruff + pytest + `openspec validate --strict`)
