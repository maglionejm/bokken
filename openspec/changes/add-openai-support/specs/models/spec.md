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
not flatten the sidekick or extraction lanes. Models SHALL come from an
explicit allowlist and SHALL belong to the selected provider. Configured
reasoning effort (`low | medium | high`) SHALL be applied by either provider to
reasoning classes, never silently ignored. Typed consumers SHALL continue to
request schema-validated structured output.

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
- **THEN** its reasoning-class request contains `low` effort rather than the default `high`

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
