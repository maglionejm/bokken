# report Specification Delta

## MODIFIED Requirements

### Requirement: Full process coverage

Both formats SHALL report the entire process and its intermediate outputs —
the brief and inputs, the stage arc including loop-backs, evidence samples
with confidence classes, problem-statement candidates with losers and why
they lost, the concept decision with dissent, prototype artifacts with
assumption mappings, the scored assumption register, facilitation moves, and
research debt — and the final outputs: the recommendation, validation flags,
dossier and handoff pointers, and model usage with an estimated cost labeled
as a list-price estimate.

The per-model usage lines SHALL carry cache-read and cache-write tokens
alongside input and output, and SHALL be priced by the same shared pricing
function the `costs` verb uses, so the report and the cost report agree on any
one session.

#### Scenario: Intermediate outputs are present

- **WHEN** a completed dojo session is exported
- **THEN** the HTML contains the problem statement, at least one losing
  option with its `why_lost`, every assumption with its score, and the
  recommendation

#### Scenario: The report's estimate includes cached tokens

- **WHEN** a session whose spend is mostly a cached prompt prefix is exported
- **THEN** the report's cost estimate prices those cache reads and cache
  writes and equals the `costs` verb total for the same session
