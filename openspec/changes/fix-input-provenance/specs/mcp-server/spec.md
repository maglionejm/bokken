# mcp-server Specification Delta

## MODIFIED Requirements

### Requirement: Actor attribution

Every state-changing operation arriving over MCP SHALL be journaled with
`actor.kind: agent` and the connected client's declared identity (client
name/version from the MCP handshake); gate resolutions and inputs submitted
over MCP SHALL therefore be distinguishable in the ledger from human terminal
actions. Attribution SHALL be applied by the server, not trusted from tool
arguments.

Attribution SHALL extend to answer content, not only to the act of submitting
it: `submit_input` SHALL stamp the handshake actor onto the stored answer, and
the engine that consumes it SHALL journal the resulting evidence with that
actor and confidence class `simulated`. The server SHALL NOT provide any way
for a client to have its answer journaled as human evidence or in a human
confidence class, and SHALL NOT accept a supplied actor for an answer.

#### Scenario: Agent-approved gate is attributed

- **WHEN** a gate is approved via `resolve_gate` from a client identifying as `claude-code`
- **THEN** the `session.gate_resolved` event's actor records kind `agent` and that client identity

#### Scenario: Attribution cannot be spoofed via arguments

- **WHEN** a tool call includes a forged actor field in its arguments
- **THEN** the journaled actor reflects the handshake identity, not the argument

#### Scenario: Submitted answer is not human evidence

- **WHEN** a client answers a pending Founder-mode question via `submit_input` and calls `run_session`
- **THEN** the `evidence.captured` event carries the client's agent actor and confidence class `simulated`, the session's ledger contains no human-attributed record, and decisions resting on that evidence carry `requires_real_validation`
