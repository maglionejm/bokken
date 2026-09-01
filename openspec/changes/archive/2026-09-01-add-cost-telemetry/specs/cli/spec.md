# cli

## ADDED Requirements

### Requirement: Costs verb

`bokken costs <name>` SHALL print a deterministic cost report derived from
replayed `model.called` events: one row per stage x prompt_id x routing
class with calls, input, output, and cache-read tokens, a list-price
estimate labeled as such, per-model subtotals with cache hit-rate, and the
run total. `--json` SHALL emit the same data as one JSON document.

#### Scenario: Costs from the terminal

- **WHEN** `bokken costs mars-lander --json` runs on a completed session
- **THEN** stdout is one JSON document whose totals equal the sum of the
  journaled usage priced at the list table
