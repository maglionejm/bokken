# stages Specification Delta

## ADDED Requirements

### Requirement: Answer-derived records carry their supplier

Every record a stage engine appends from an answer obtained through the
orchestrator's input port — interview evidence and abstentions in Empathize,
read-through evidence and assumption scores in the Test stage, founder-
contributed options and the convergence decision in Ideate — SHALL be
attributed to the actor that supplied that answer, and SHALL take its
confidence class from that supplier: the engine's stated human class
(`reported` for interview answers, `observed` for the read-through) when a
human answered, and `simulated` when anything else did. The source label of a
machine-supplied answer SHALL name it as machine-supplied and SHALL NOT present
it as human interview or read-through material. A convergence decision SHALL
carry `requires_real_validation` unless a human made the selection.

Relaying a human's words through a machine surface SHALL NOT upgrade their
class: only participation that arrives from a human surface produces human
evidence.

#### Scenario: Agent-supplied interview answer is labeled

- **WHEN** an MCP client submits the answer to a pending Empathize question and the run consumes it
- **THEN** the `evidence.captured` record carries the client's agent actor, `confidence_class: simulated`, and a source naming it agent-supplied — never `actor.kind: human` and never `reported`

#### Scenario: Human founder answer is unaffected

- **WHEN** the human founder answers the same question at the terminal
- **THEN** the record carries `actor.kind: human` with confidence class `reported` and source `founder interview`

#### Scenario: Agent-picked concept is flagged

- **WHEN** the Ideate convergence selection is supplied by a non-human client
- **THEN** the `decision.recorded` event is attributed to that client and carries `requires_real_validation: true`
