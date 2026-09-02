# cli Specification Delta

## MODIFIED Requirements

### Requirement: Costs verb

`bokken costs <name>` SHALL print a deterministic cost report derived from
replayed `model.called` events: one row per stage x prompt_id x routing
class with calls, input, output, and cache-read tokens, a list-price
estimate labeled as such, per-model subtotals with cache hit-rate, and the
run total. The report SHALL also carry grounding health folded from the same
journal: persona turns, how many of them abstained, and how many of those
abstentions the grounding backstop forced because a citation did not resolve
to a corpus span, reported as both a count and a share of persona turns. That
share SHALL be distinguishable from honest research gaps, so a delegated lane
made cheaper cannot degrade citation quality invisibly. `--json` SHALL emit the
same data as one JSON document.

#### Scenario: Costs from the terminal

- **WHEN** `bokken costs mars-lander --json` runs on a completed session
- **THEN** stdout is one JSON document whose totals equal the sum of the
  journaled usage priced at the list table

#### Scenario: Backstop-forced abstentions are visible next to spend

- **WHEN** a run's persona turns include answers whose citations did not resolve to a corpus span
- **THEN** the costs report counts those turns separately from honest abstentions and reports their share of persona turns

#### Scenario: One trace, one number

- **WHEN** a session containing a cache-heavy call is priced by the cost
  report and by the exported report's model usage lines
- **THEN** both quote the same total for that session
