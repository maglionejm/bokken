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

The router SHALL resolve invocations by routing class using the provider
selected in the immutable session config. Anthropic defaults SHALL be:
`research` and `challenge` → `claude-fable-5` at high effort; `cognition` and
`generation` → `claude-opus-5` with adaptive thinking at high effort;
`sidekick` → `claude-opus-5`; and `extraction` → `claude-haiku-4-5`. OpenAI
defaults SHALL be: `research`, `challenge`, `cognition`, and `generation` →
`gpt-5`; and the economical `sidekick` and `extraction` lanes → `gpt-5-mini`.
Fable requests SHALL retain their server-side refusal fallback to
`claude-opus-4-8`.

Provider and per-class routing SHALL be fixed at session creation and journaled
in the config snapshot. A single-model convenience override SHALL affect only
frontier classes (`research`, `challenge`, `cognition`, `generation`) and SHALL
not flatten the sidekick or extraction lanes. Models SHALL come from a single
model registry that declares each model's provider, list price, and whether it
may serve frontier classes or accept a reasoning parameter; the allowlist,
provider map, and cost estimates SHALL derive from that registry. A routing
configuration SHALL be rejected at session creation when a model cannot serve
its class or cannot accept the configured effort, rather than failing at first
dispatch. Configured reasoning effort (`low | medium | high`) SHALL be applied
by either provider to frontier classes only, never silently ignored and never
sent to a model that rejects it. Typed consumers SHALL continue to request
schema-validated structured output. Every `model.called` record SHALL name the
model that served the call alongside the model routing requested, and journaled
agent provenance SHALL name the model routed for that agent's lane.

#### Scenario: Class resolves to configured model

- **WHEN** an extraction call is made in an Anthropic session with default routing
- **THEN** the request targets `claude-haiku-4-5` and the journal records class `extraction`

#### Scenario: Research and challenge run on Fable 5 high

- **WHEN** a persona interview turn and test evaluation use Anthropic defaults
- **THEN** both target Fable 5 at high effort without a thinking parameter and with the server-side Opus fallback

#### Scenario: Execution and documentation run on Opus high

- **WHEN** define clustering and handoff generation use Anthropic defaults
- **THEN** both target Opus 5 with adaptive thinking at high effort

#### Scenario: OpenAI defaults preserve Fusion economics

- **WHEN** an OpenAI session dispatches frontier, sidekick, and extraction calls without overrides
- **THEN** frontier calls target `gpt-5` while sidekick and extraction target `gpt-5-mini`

#### Scenario: Frontier model override does not flatten lanes

- **WHEN** an OpenAI session is created with frontier model override `gpt-5.6-luna`
- **THEN** the four frontier classes target that model and sidekick/extraction remain `gpt-5-mini`

#### Scenario: Reasoning effort is honored

- **WHEN** either provider is configured with reasoning effort `low`
- **THEN** its frontier-class request contains `low` effort rather than the default `high`, and sidekick/extraction requests carry no reasoning parameter

#### Scenario: Impossible routing is refused at creation

- **WHEN** a session requests an extraction-grade model for a frontier class, or an effort setting on a model that rejects reasoning parameters
- **THEN** creation fails with a routing configuration error and no session is journaled

#### Scenario: Provenance names the serving model

- **WHEN** an OpenAI session journals facilitator, persona, researcher, or tester contributions
- **THEN** each actor's model is the OpenAI model routed for that contribution's lane, and `model.called` records both the serving model and the requested model

#### Scenario: Routing table is part of the session snapshot

- **WHEN** a session is created with provider, effort, or routing overrides
- **THEN** `session.created` contains that immutable model configuration

#### Scenario: Sidekick handles the mechanical reads

- **WHEN** an interview turn faces a corpus above the delegation threshold
- **THEN** a sidekick call retrieves source-marked spans, the frontier turn receives only those slices, and both calls are journaled

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

### Requirement: Web-search-enabled research calls

The router SHALL accept a per-invocation `web_search` option that the
provider maps to its server-side web search tool; it SHALL be honored only
for `research`-class calls, and the resulting `model.called` event SHALL
record that web search was enabled. The fake provider SHALL accept the
option so tests run offline.

#### Scenario: Web search reaches the provider request

- **WHEN** a research-class call is invoked with `web_search=True`
- **THEN** the provider request includes the server-side web search tool and the journaled call records `web_search: true`

#### Scenario: Non-research classes cannot search

- **WHEN** a cognition-class call passes `web_search=True`
- **THEN** the router rejects the invocation with a typed error

### Requirement: Parallel prompt caches

Prompts MAY declare a cache split: the provider SHALL send everything before
the split as a cache-controlled block so each lane keeps its own persistent
cached prefix (the sidekick's corpus, the persona panel's corpus, the lens
prompts' shared option set, the test panel's artifact). Per-call journaled usage
SHALL carry cache-read tokens so `bokken costs` can report hit rates. Switching
lanes SHALL never invalidate the other lane's cache (they are per-model by
construction).

A template that declares a cache split SHALL place every parameter that is
shared across the calls in its loop before the split, and every parameter that
varies per call after it, so that the cacheable prefix is byte-identical for
each call in the loop. A cache split SHALL NOT be declared on a template whose
prefix varies per call or is smaller than the routed models' minimum cacheable
prefix, since a cache write costs more than fresh input and such a prefix could
never be read back. Delegated retrieval that feeds a cached prefix SHALL be
reused across the calls that share that prefix rather than re-issued per call.

Rendered prompt text SHALL be identical whether or not a template declares a
split - the marker is provider framing only, never model-visible content - so
the journaled prompt hash keeps matching the wire payload for every adapter.

#### Scenario: The corpus is paid for once

- **WHEN** twelve interview turns run against the same corpus within the cache TTL
- **THEN** the corpus tokens are written once and read from cache thereafter, and the cost report shows a non-zero cache hit rate

#### Scenario: Shared material leads the persona turn

- **WHEN** several personas answer one question over one corpus
- **THEN** each rendered persona turn carries a byte-identical cacheable prefix holding the corpus, with the persona and the question after the split

#### Scenario: One artifact serves the whole assumption register

- **WHEN** a test panel evaluates one prototype artifact once per assumption
- **THEN** the artifact sits in the cacheable prefix and the persona and assumption under test sit after the split

#### Scenario: One option set serves every convergence lens

- **WHEN** the feasibility, viability, and desirability lenses vote on the same frozen options
- **THEN** the problem, criteria, and option set are written to cache once and read back by the remaining lenses, with each lens's own instructions after the split

#### Scenario: Retrieval is not re-issued per persona

- **WHEN** an interview turn faces a corpus above the delegation threshold and every persona on the panel is asked that question
- **THEN** the sidekick retrieves the spans once and every persona turn receives that identical retrieval

#### Scenario: A prefix too small to cache declares no split

- **WHEN** a per-call loop's shared material is smaller than the routed models' minimum cacheable prefix
- **THEN** the template still orders that material before the varying material but declares no cache split

### Requirement: Frontier judgment is never delegated

Calls that feed a `decision.recorded` (selection, lens votes, skeptic,
recommendation, specification) and persona voice SHALL remain on the
frontier lanes (`research`/`challenge`/`cognition`/`generation`); the
sidekick's concluding UI verdict SHALL be confirmed by a research-class
call before it is journaled.

#### Scenario: Verdicts escalate

- **WHEN** the sidekick proposes a feature-test verdict
- **THEN** a research-class call confirms it and the journaled verdict comes from the frontier

### Requirement: OpenAI provider adapter

The system SHALL support OpenAI Responses API models through the existing
`ModelRouter` seam, including plain text, Pydantic structured output, streaming,
and explicitly authorized web search calls. The OpenAI SDK SHALL remain an
optional dependency imported only when an OpenAI model is dispatched. Internal
Anthropic cache markers SHALL never be sent to OpenAI; their prefix and suffix
order SHALL be preserved for OpenAI implicit prefix caching. Usage, cached input,
response id, model, stop status, and failures SHALL be normalized and journaled
through the existing provider-neutral contract.

#### Scenario: OpenAI structured call

- **WHEN** a session routes a call to an OpenAI model with a Pydantic schema
- **THEN** the provider returns parsed data and the router appends exactly one `model.called` event with usage, model, response id, and status

#### Scenario: OpenAI cache prefix

- **WHEN** a rendered prompt contains the internal cache split marker
- **THEN** OpenAI receives the prefix followed by the suffix without the marker

#### Scenario: OpenAI provider failure

- **WHEN** the SDK or network raises an exception
- **THEN** the router returns an error outcome and journals the failed call

#### Scenario: Offline core installation

- **WHEN** Bokken is installed without the OpenAI optional extra
- **THEN** imports, fake-provider tests, and Anthropic sessions continue to work

#### Scenario: Unavailable provider refuses instead of failing per call

- **WHEN** an OpenAI session runs without the optional extra installed or without an API key
- **THEN** the run refuses with a provider-unavailable error before any stage work is journaled

#### Scenario: Truncated or refused OpenAI response

- **WHEN** an OpenAI response ends incomplete at the output cap, or carries a refusal
- **THEN** the router journals `truncated` with real usage, or `refused`, rather than a provider error

### Requirement: Delegation must beat cached retrieval

Fusion delegation to the sidekick SHALL be triggered only where it beats sending
the corpus itself, accounting for the persona turn's cached corpus prefix: an
undelegated corpus is paid once at the cache-write premium and read back at a
fraction of fresh input, while delegation additionally pays the sidekick's
retrieval output at frontier output prices for every distinct question. The
delegation threshold SHALL be documented in the code with that rationale, and
crossing it SHALL remain journaled as a sidekick call.

#### Scenario: A moderate corpus is sent rather than delegated

- **WHEN** an interview turn faces a corpus below the delegation threshold
- **THEN** no sidekick call is made and the corpus is sent as the turn's cacheable prefix

#### Scenario: A very large corpus is still delegated

- **WHEN** an interview turn faces a corpus above the delegation threshold
- **THEN** a sidekick call retrieves source-marked spans, the frontier turn receives only those slices, and both calls are journaled
