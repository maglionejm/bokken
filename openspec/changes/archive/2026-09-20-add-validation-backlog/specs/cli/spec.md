# cli

## ADDED Requirements

### Requirement: Backlog verb

`bokken backlog <name>` SHALL print a deterministic, replay-derived validation
to-do list built from the journal alone with no model call. It SHALL rank the
session's untested and contradicted assumptions by impact x uncertainty
(reading the journaled `impact` and `uncertainty` on each assumption and the
`score` from its latest scoring), highest first, and SHALL fold every open
research-debt abstention in as a backlog item. Supported assumptions SHALL NOT
appear. The default output SHALL be a plain terminal table with one row per
item carrying at least rank, kind (`assumption` or `research_debt`), impact,
uncertainty, confidence class, source/provenance, and the statement or open
question. Every item SHALL carry its `confidence_class` and its session
provenance, and a simulated-only backlog SHALL keep the simulated framing
(restating the dojo banner and that the run still requires real validation) so
it is never read as validated fact. The report SHALL include a single
"what would flip the verdict" line derived from the register versus the test
recommendation: since the recommendation is a challenge-class judgement over
the register rather than a mechanical cutoff, that line SHALL state the
register counts (supported / contradicted / untested) and the gap plainly —
how many untested items remain to resolve and that any contradicted item is a
standing kill-or-iterate signal — rather than asserting an invented threshold.
`--json` SHALL emit exactly one `BacklogResult`-shaped JSON document with the
ranked items, the register counts, the flip-the-verdict text, and the honesty
flags; `--format csv` and `--format markdown` SHALL emit an issue-tracker
checklist of the same ranked items. Exit codes SHALL follow the CLI output
discipline: `2` for an unknown session, `0` otherwise (including an empty
backlog).

#### Scenario: Ranked backlog with CSV and markdown export

- **WHEN** `bokken backlog mars-lander` runs on a completed dojo session whose
  register holds untested and contradicted assumptions plus open research debt,
  and then the same command is run with `--format csv` and with
  `--format markdown`
- **THEN** the terminal table lists the assumption and research-debt items
  ranked by impact x uncertainty with each item's confidence class and source,
  shows the "what would flip the verdict" line with the register counts, and
  the `--format csv` and `--format markdown` runs emit the same ranked items as
  an issue-tracker checklist

#### Scenario: Empty backlog when nothing is untested

- **WHEN** `bokken backlog mars-lander --json` runs on a session whose
  assumptions are all supported and which has no open research debt
- **THEN** stdout is one `BacklogResult` JSON document with an empty item list,
  the register counts, and a flip-the-verdict line stating there is nothing
  left to test, and the exit code is `0`

#### Scenario: A simulated-only backlog keeps the simulated framing

- **WHEN** `bokken backlog mars-lander --json` runs on a dojo session whose
  assumption scores came only from the synthetic panel
- **THEN** every item carries `confidence_class` `simulated`, and the payload
  keeps the simulated framing (dojo banner and requires-real-validation), so
  the backlog is not presented as validated fact
