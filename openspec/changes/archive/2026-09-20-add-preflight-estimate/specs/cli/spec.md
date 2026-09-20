## ADDED Requirements

### Requirement: Estimate verb

`bokken estimate <brief.json>` SHALL predict a run's token usage and
list-price cost **before** any session is created, by derivation only - no
`ModelRouter` call, no provider SDK, no network, and no journal written. It
SHALL accept `--panel-size` (default 6, matching `bokken new`), `--provider`,
and `--model`, and SHALL price on the **served** model that the brief's
provider/model routing would resolve to (via the same routing resolution a
created session uses), reusing the single pricing function so the estimate and
a later `bokken costs` receipt speak one pricing language. The estimate SHALL
be built from the per-routing-class token profile and the run's executed
prompt set, scaling the research lane with panel size (more personas -> more
per-persona research-lane calls). Output SHALL be a **low-high USD range**
(never a single false-precision number) plus a **per-functional-lane
breakdown** - exploration / research / synthesis, using the same lane
vocabulary as the costs functional rollup - each lane reporting its estimated
calls, tokens, and cost, and the three lane costs SHALL sum to the estimate's
point figure. The surface SHALL be labeled a **modeled estimate** and SHALL
state its assumptions - the panel size assumed and that the token profile is
an illustrative modeled profile, not a measurement of this brief - and SHALL
NOT present the figure as a guaranteed or actual cost. `--json` SHALL emit one
`EstimateResult` JSON document on stdout carrying the range, the per-lane
breakdown, the assumptions, and the modeled-estimate caveat; a missing or
schema-invalid brief file SHALL exit `2` with a stderr message and write no
model call.

#### Scenario: Modeled estimate with a range and lane breakdown

- **WHEN** `bokken estimate brief.json --panel-size 6 --json` is invoked with a
  valid brief
- **THEN** stdout is one `EstimateResult` JSON document carrying a low-high USD
  range whose low does not exceed its high, an exploration/research/synthesis
  lane breakdown whose lane costs sum to the point estimate, a stated
  assumption that the panel size is 6 and the profile is a modeled estimate,
  and no session is created and no model is called

#### Scenario: The estimate scales with panel size

- **WHEN** `bokken estimate brief.json --panel-size 10` and
  `bokken estimate brief.json --panel-size 4` are run against the same brief
- **THEN** the panel-size-10 estimate's cost and research-lane call count are
  strictly greater than the panel-size-4 estimate's, because more personas add
  per-persona research-lane calls

#### Scenario: Honest about being an estimate, never a guarantee

- **WHEN** `bokken estimate brief.json` prints its human-readable output
- **THEN** the output labels the figure a modeled estimate drawn from an
  illustrative profile, states it is not a measurement or a guarantee, and
  points to `bokken costs` for the actual list price once a run exists

#### Scenario: A missing brief is refused before any work

- **WHEN** `bokken estimate does-not-exist.json` is invoked
- **THEN** the command exits `2` with a stderr message naming the unreadable
  brief and no session, journal, or model call is produced
