# stages Specification Delta

## ADDED Requirements

### Requirement: Contribution provenance follows the producing call

Every record a stage engine appends SHALL be attributed to whatever actually
produced it. A record derived from one model call — a clustered insight, a
selected problem statement, a persona utterance or evaluation or outcome score,
a registered assumption, a generated prototype artifact, a UI review, a
kill/iterate/proceed recommendation — SHALL carry the served model of that
call, obtained from the call's own outcome. Engines SHALL NOT read the routing
table to attribute a contribution; the model that answered is not knowable
before the call returns, so there is nothing correct to look up beforehand.

A record that no single call produced SHALL claim no model: facilitation moves,
deterministic tallies (the Ulwick opportunity ranking, the convergence vote
tally and the option kills that follow from it), files the engine renders from
records already on the ledger, and a governance refusal that dispatched no call
(concept research skipped for want of `allow_web_research`). Where a bounded
agentic loop concludes on a specific call's verdict — the per-feature UI test —
the record SHALL name that call's server, and SHALL claim no model when the
loop exhausted its step budget without any call concluding it.

Attribution SHALL NOT be weakened by a governance rewrite: when the grounding
backstop converts a persona's answer into an abstention because its citations
did not resolve, the abstention SHALL still name the served model of the turn
that produced the rejected answer.

#### Scenario: A derived record names its producing call

- **WHEN** Define journals insights from its clustering call and a decision from its selection call
- **THEN** each record's actor names the model that served that specific call, which may differ from the model routing requested

#### Scenario: A deterministic tally names no model

- **WHEN** Empathize journals the computed opportunity ranking and Ideate journals the convergence decision and the options it kills
- **THEN** those records carry an agent actor with no model, because the harness computed them from records already on the ledger

#### Scenario: A skipped escalation is not attributed to a model

- **WHEN** the brief does not declare `allow_web_research: true` and concept research is journaled as research debt
- **THEN** the abstention carries no model, since no call was dispatched

#### Scenario: A rewritten persona turn keeps its speaker's model

- **WHEN** the grounding backstop rejects a turn's citations and journals an abstention instead
- **THEN** the abstention carries the persona's `persona_id` and the served model of that turn's call
