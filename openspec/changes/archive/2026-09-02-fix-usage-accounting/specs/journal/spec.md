# journal Specification Delta

## MODIFIED Requirements

### Requirement: Replay to session state

The system SHALL derive session state exclusively by folding the journal in `seq` order into a typed state: current stage, session mode and brief, pending gate (if any), evidence index by confidence class, insight/POV list with grounding links, idea lineage graph, assumption register, decision log with dissent, budget counters (tokens spent per routing class), and stop status. Replay SHALL be deterministic: the same journal always yields the same state.

Budget counters SHALL count every token bucket the provider billed — uncached
input, output, cache read, and cache write — at face value, because budgets
are expressed as token counts and provider adapters report the cached prompt
prefix disjointly from `input_tokens`. No billed bucket SHALL be invisible to
the meter, and the meter SHALL NOT apply prices or weights: pricing belongs to
the cost report.

#### Scenario: Resume reconstructs exactly where the run left off

- **WHEN** a session that stopped mid-`ideate` is reopened and replayed
- **THEN** the derived state reports stage `ideate`, the same idea lineage and budgets as before the stop, and the run continues without re-executing prior events

#### Scenario: Replay is pure

- **WHEN** the same journal file is replayed twice
- **THEN** both derived states are equal field-for-field

#### Scenario: A cached prompt prefix is not invisible to the budget

- **WHEN** a `model.called` event reports 5,000 input, 500 output, and 195,000
  cache-read tokens
- **THEN** `tokens_spent` for that routing class is 200,500, and a session
  budget of 100,000 total tokens is exhausted
