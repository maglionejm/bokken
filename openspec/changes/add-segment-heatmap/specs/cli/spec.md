## ADDED Requirements

### Requirement: Opportunities verb

`bokken opportunities <name>` SHALL print a deterministic segment × outcome
opportunity matrix derived purely from the replayed journal — no model calls —
addressing the session by name through the core. Rows SHALL be the segments
present on the session's personas and columns SHALL be the desired outcomes;
each cell SHALL show the mean Ulwick opportunity score over the personas of that
segment who scored that outcome, together with that cell's sample size (the
number of such personas). The opportunity score SHALL be computed by the same
definition the report uses, so the verb and the report agree for any one
session. A cell whose sample size is below two SHALL be flagged as
low-confidence in the output. For a dojo session the output SHALL state that the
matrix is simulated and requires validation with real users. `--json` SHALL emit
the same data as one JSON document with a stable shape (segments, outcomes, and
per-cell `score`, sample size `n`, and low-confidence flag). A session with no
scored outcomes SHALL exit 2 with a message naming what is missing, and an
unknown session SHALL exit 2 per the CLI's output discipline.

#### Scenario: The matrix is computed with per-cell sample sizes

- **WHEN** `bokken opportunities mars-lander --json` runs on a completed session
  whose personas span two segments and scored the desired outcomes
- **THEN** stdout is one JSON document whose cells are keyed by
  `(segment, outcome)`, each carrying the mean opportunity score over that
  segment's personas for that outcome and the count `n` of personas behind it,
  and the totals reconcile with the report's derivation for the same session

#### Scenario: A thin cell is flagged low-confidence

- **WHEN** only one persona in a segment scored a given outcome and
  `bokken opportunities mars-lander` is run
- **THEN** that cell shows its score and sample size `n=1` and is flagged
  low-confidence in both the human matrix and the `--json` output

#### Scenario: Dojo framing carries onto the matrix

- **WHEN** `bokken opportunities mars-lander` is run on a dojo session
- **THEN** the output states the matrix is simulated and requires validation
  with real users

#### Scenario: No scored outcomes is refused

- **WHEN** `bokken opportunities mars-lander` is run on a session that never
  scored desired outcomes
- **THEN** the command exits 2 with a message naming that no outcome scores were
  journaled, and writes no matrix
