# models Specification Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
