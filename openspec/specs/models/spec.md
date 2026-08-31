# models Specification

## Purpose
The models capability is the single seam between Bokken and LLM providers: routing classes map each kind of cognitive work to a model and parameters, every invocation is journaled with cost, and structured outputs are validated at the boundary — so runs are auditable, budgetable, and testable offline.

## Requirements

### Requirement: Single model seam

All LLM invocations in the harness SHALL go through the `ModelRouter`; no stage, kata, or panel code may call a provider SDK directly. The router SHALL be injectable, and a fake router SHALL allow the entire harness to run offline in tests.

#### Scenario: Offline test run

- **WHEN** the test suite runs a full session with a fake router and no network
- **THEN** every engine and move executes normally and no provider call is attempted

### Requirement: Routing classes

The router SHALL resolve invocations by routing class, with these MVP classes and defaults: `cognition` (stage reasoning, synthesis, facilitation judgment, persona turns) → `claude-opus-4-8` with adaptive thinking (`{type: "adaptive"}`); `extraction` (lightweight classification and signal extraction: novelty scoring, quota counting, claim detection) → `claude-haiku-4-5`; `generation` (long-form artifact generation) → `claude-opus-4-8` with streaming. Routing SHALL be configurable per session at creation (model per class within an allowlist) and the resolved routing table SHALL be journaled in the session config snapshot. Requests in the `cognition` and `generation` classes SHALL use structured outputs with schema validation whenever the consumer expects typed data.

#### Scenario: Class resolves to configured model

- **WHEN** an `extraction` call is made in a session with default routing
- **THEN** the request targets `claude-haiku-4-5` and the journaled model event records class `extraction`

#### Scenario: Routing table is part of the session snapshot

- **WHEN** a session is created with a routing override
- **THEN** `session.created`'s config snapshot contains the full resolved routing table

### Requirement: Every call is journaled

Every provider invocation SHALL produce exactly one `model.called` event containing: routing class, model id, prompt identifier and content hash (never full prompt text), request id from the provider, token usage (input, output, cache read/write where reported), outcome status (`ok | refused | error | truncated`), and duration. Failed or refused calls SHALL be journaled with their status before any retry or fallback occurs.

#### Scenario: Usage flows into budgets

- **WHEN** a `cognition` call completes with reported token usage
- **THEN** the `model.called` event carries that usage and the session's budget counters reflect it on next replay

#### Scenario: Refusal is recorded

- **WHEN** the provider returns a refusal stop reason
- **THEN** a `model.called` event with status `refused` is journaled and the caller receives a typed refusal outcome, not an exception-free empty string

### Requirement: Structured output validation at the boundary

When an invocation declares an expected schema, the router SHALL validate the response against it and return typed data; validation failures SHALL surface as typed errors (journaled with status `error`) — malformed model output SHALL never propagate into session state or the journal as if valid.

#### Scenario: Schema violation is contained

- **WHEN** a model response fails schema validation
- **THEN** no derived event is written from it, the model event records the failure, and the caller can retry per policy

### Requirement: Budget enforcement hooks

Before dispatching, the router SHALL check the session's remaining token budget for the routing class (derived from replayed usage) and refuse dispatch when the budget is exhausted, returning a typed budget-exhausted outcome that the orchestrator translates into `session.stopped` (`budget_exhausted`).

#### Scenario: Dispatch refused over budget

- **WHEN** a call is requested with the class budget already spent
- **THEN** no provider request is made and the budget-exhausted outcome propagates to the orchestrator's stopping rule

### Requirement: Prompt versioning

Every prompt template used by engines, kata moves, and personas SHALL have a stable identifier and version; the identifier+version and the rendered-content hash SHALL appear in the corresponding `model.called` events, so any journaled output can be traced to the exact prompt that produced it.

#### Scenario: Prompt change is visible in the ledger

- **WHEN** a prompt template is revised and a new run executes
- **THEN** the new run's model events carry the new version while old journals retain the old one
