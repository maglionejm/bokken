# cli Specification Delta

## MODIFIED Requirements

### Requirement: Costs verb

`bokken costs <name>` SHALL print a deterministic cost report derived from
replayed `model.called` events: one row per stage x prompt_id x routing
class with calls, input, output, cache-read and cache-write tokens, a
list-price estimate labeled as such, per-model subtotals with cache hit-rate,
and the run total. `--json` SHALL emit the same data as one JSON document.

Every surface that estimates cost SHALL price a call through one shared
pricing function covering all four billed buckets, so the same journaled trace
is never quoted at two different numbers. Cache multipliers SHALL be applied
per provider, derived from the model registry's provider and list price:
Anthropic cache reads at a tenth of input and cache writes at a premium over
input; OpenAI cached input at a reduced rate with no separate cache-write
charge. Provider-side tool fees (such as web search request charges) are not
reported in provider usage metadata and SHALL be omitted rather than
estimated.

#### Scenario: Costs from the terminal

- **WHEN** `bokken costs mars-lander --json` runs on a completed session
- **THEN** stdout is one JSON document whose totals equal the sum of the
  journaled usage priced at the list table

#### Scenario: One trace, one number

- **WHEN** a session containing a cache-heavy call is priced by the cost
  report and by the exported report's model usage lines
- **THEN** both quote the same total for that session
