# Proposal: fix-input-provenance

## Why

`submit_input` on the MCP surface took an answer and stored it with no
attribution. The Empathize engine then journaled that text as
`evidence.captured` with `actor: {kind: human, name: founder}`,
`source: "founder interview"`, and `confidence_class: "reported"` — the
strongest class the harness has for interview material. An agent client could
therefore write its own sentences into the ledger as human testimony, which is
exactly the laundering the constitution's honesty rules forbid (Blueprint §3),
and it falsified `docs/mcp.md`'s promise that identity is stamped server-side
and cannot be supplied through tool arguments. The Test engine's founder
read-through had the same hole in the `observed` class, and Ideate attributed
agent-picked options and convergence decisions to the founder.

The root cause is the input-port seam: `InputPort.ask` returned a bare string,
so an answer arrived at the append boundary carrying no trace of who supplied
it and every engine had to assume the human founder. `resolve_gate` already
stamps handshake identity via `_client_actor(ctx)`; the answer path was never
given that treatment.

## What Changes

- `InputPort.ask` returns an `Answer` (text + the `Actor` that supplied it)
  instead of a bare string. Provenance is mandatory: `Answer.actor` has no
  default, so no port can hand a stage an unattributed answer.
- `TerminalInputPort` stamps the human founder; the MCP `MailboxPort` stamps
  the submitting client's handshake actor, carried through `answers.json`.
- `submit_input` takes the MCP `Context` and stamps `_client_actor(ctx)`, the
  same server-side identity `resolve_gate` uses; it reports `attributed_to`.
- Engines journal the supplier's actor, and derive the confidence class from
  the supplier: a human answer keeps the call site's class (`reported` in
  Empathize, `observed` in the Test read-through); a machine-supplied answer is
  `simulated` at the record level with source `agent-supplied (<client>)`.
- The convergence decision in Ideate is attributed to whoever actually picked,
  and carries `requires_real_validation` unless a human picked it.
- `docs/mcp.md` states what the mailbox does and does not confer.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `orchestrator`: the input-port seam carries the answer's supplier.
- `stages`: engines journal answer-derived records with the supplier's
  provenance and an honest confidence class.
- `mcp-server`: `submit_input` is attributed from the handshake, like every
  other state-changing tool.

## Impact

`src/bokken/orchestrator/runner.py`, `src/bokken/cli/wiring.py`,
`src/bokken/mcp/server.py`, `src/bokken/stages/{empathize,testing,ideate}.py`,
`src/bokken/journal/__init__.py` (exports `ConfidenceClass`), `docs/mcp.md`,
and tests. No journal schema change: existing records stay valid and are never
migrated. Nothing derived needed changing — `panel.governance
.requires_real_validation` and the Dossier's synthetic labeling already key on
`simulated`, so the new class propagates through both unaltered.
