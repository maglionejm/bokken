# models

## MODIFIED Requirements

### Requirement: Routing classes

The router SHALL resolve invocations by routing class, with these classes and
defaults: `research` (interview program design, persona interview turns,
follow-ups, desired-outcome derivation) → `claude-fable-5` at `effort: high`;
`challenge` (skeptic challenges, convergence lenses, prototype evaluation,
kill/iterate/proceed recommendation) → `claude-fable-5` at `effort: high`;
`cognition` (stage execution mechanics: clustering, candidate drafting,
selection, assumption enumeration, fidelity choice, idea generation) →
`claude-opus-5` with adaptive thinking at `effort: high`; `generation`
(long-form artifact and specification writing) → `claude-opus-5` with
adaptive thinking at `effort: high` and streaming; `extraction` (lightweight
classification) → `claude-haiku-4-5`. Fable 5 requests SHALL omit the
`thinking` parameter and SHALL opt into the server-side refusal fallback to
`claude-opus-4-8`; a refusal that survives the fallback chain is journaled as
`refused`. Routing SHALL remain configurable per session at creation (model
per class within an allowlist that includes `claude-fable-5`, `claude-opus-5`, and `claude-sonnet-5`) and the
resolved routing table SHALL be journaled in the session config snapshot.
Requests in reasoning classes SHALL use structured outputs with schema
validation whenever the consumer expects typed data.

#### Scenario: Class resolves to configured model

- **WHEN** an `extraction` call is made in a session with default routing
- **THEN** the request targets `claude-haiku-4-5` and the journaled model event records class `extraction`

#### Scenario: Research and challenge run on Fable 5 high

- **WHEN** a persona interview turn and a test evaluation are dispatched with default routing
- **THEN** both requests target `claude-fable-5` with `output_config.effort` `high`, no `thinking` parameter, and a server-side fallback to `claude-opus-4-8`

#### Scenario: Execution and documentation run on Opus high

- **WHEN** a define clustering call and a handoff specification call are dispatched with default routing
- **THEN** both requests target `claude-opus-5` with adaptive thinking and `output_config.effort` `high`

#### Scenario: Routing table is part of the session snapshot

- **WHEN** a session is created with a routing override
- **THEN** `session.created`'s config snapshot contains the full resolved routing table
