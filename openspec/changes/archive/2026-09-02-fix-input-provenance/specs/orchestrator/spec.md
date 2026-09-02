# orchestrator Specification Delta

## ADDED Requirements

### Requirement: Input provenance

The input-port seam SHALL carry the provenance of whoever supplied an answer,
not only the answer text. `InputPort.ask` SHALL return an answer object
carrying the text and the `Actor` that supplied it; that actor SHALL be
mandatory, so no port can hand a stage engine an unattributed answer. The
terminal port SHALL report a human actor (the person typing at the prompt); any
port that brokers answers from elsewhere SHALL report the actor it received
them from — for the MCP input mailbox, the submitting client's handshake
identity. Ports SHALL NOT accept a supplier identity from the answer content or
from a caller's arguments.

Records derived from an answer SHALL be journaled with the supplying actor, and
their confidence class SHALL be derived from that actor: a human supplier keeps
the class the capturing engine states for human participation, and any
non-human supplier SHALL yield `simulated`. No answer-derived record SHALL be
journaled with `actor.kind: human` unless the answer came from a human
supplier.

#### Scenario: Terminal answer stays human

- **WHEN** a human types an interview answer at the CLI prompt
- **THEN** the port returns that text with a human actor, and the record the engine appends carries `actor.kind: human` and the engine's human confidence class

#### Scenario: Brokered answer keeps its real supplier

- **WHEN** an answer reaches an engine through a port that received it from a non-human client
- **THEN** the record the engine appends carries that client's actor with `actor.kind: agent` and confidence class `simulated`, and nothing in the ledger attributes the answer to a human
