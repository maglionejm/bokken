# models Specification Delta

## MODIFIED Requirements

### Requirement: Routing classes

The router SHALL resolve invocations by routing class using the provider
selected in the immutable session config. Anthropic defaults SHALL be:
`research` and `challenge` → `claude-fable-5` at high effort; `cognition` and
`generation` → `claude-opus-5` with adaptive thinking at high effort;
`sidekick` → `claude-sonnet-5`; and `extraction` → `claude-haiku-4-5`. OpenAI
defaults SHALL be: `research`, `challenge`, `cognition`, and `generation` →
`gpt-5`; and the economical `sidekick` and `extraction` lanes → `gpt-5-mini`.
The delegated `sidekick` lane SHALL never default to a model priced at or above
the models serving the judgment lanes it delegates for: the lane exists to keep
mechanical reading off frontier prices. Fable requests SHALL retain their
server-side refusal fallback to `claude-opus-4-8`.

Provider and per-class routing SHALL be fixed at session creation and journaled
in the config snapshot. A single-model convenience override SHALL affect only
frontier classes (`research`, `challenge`, `cognition`, `generation`) and SHALL
not flatten the sidekick or extraction lanes. Models SHALL come from a single
model registry that declares each model's provider, list price, the set of
routing classes it may serve, and whether it accepts a reasoning parameter; the
allowlist, provider map, and cost estimates SHALL derive from that registry.
The extraction-grade model SHALL declare the `extraction` class only, so
routing it to any other class — the delegated sidekick lane included — is
refused rather than merely discouraged. A routing configuration SHALL be
rejected at session creation when a model may not serve its class or cannot
accept the configured effort, rather than failing at first dispatch. Configured
reasoning effort (`low | medium | high`) SHALL be applied by either provider to
frontier classes only, never silently ignored and never sent to a model that
rejects it. Typed consumers SHALL continue to request schema-validated
structured output. Every `model.called` record SHALL name the model that served
the call alongside the model routing requested, and journaled agent provenance
SHALL name the model routed for that agent's lane.

#### Scenario: Class resolves to configured model

- **WHEN** an extraction call is made in an Anthropic session with default routing
- **THEN** the request targets `claude-haiku-4-5` and the journal records class `extraction`

#### Scenario: Research and challenge run on Fable 5 high

- **WHEN** a persona interview turn and test evaluation use Anthropic defaults
- **THEN** both target Fable 5 at high effort without a thinking parameter and with the server-side Opus fallback

#### Scenario: Execution and documentation run on Opus high

- **WHEN** define clustering and handoff generation use Anthropic defaults
- **THEN** both target Opus 5 with adaptive thinking at high effort

#### Scenario: Delegated reads stay off frontier prices

- **WHEN** an Anthropic session dispatches a sidekick corpus retrieval or UI-stepping call without overrides
- **THEN** it targets `claude-sonnet-5`, whose input and output list prices are both below those of the models serving `research`, `challenge`, `cognition`, and `generation`

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

#### Scenario: The extraction-grade model is refused on the sidekick lane

- **WHEN** a session routes `claude-haiku-4-5` to the `sidekick` class, or to any class other than `extraction`
- **THEN** creation fails with a routing configuration error naming the classes that model may serve

#### Scenario: Provenance names the serving model

- **WHEN** an OpenAI session journals facilitator, persona, researcher, or tester contributions
- **THEN** each actor's model is the OpenAI model routed for that contribution's lane, and `model.called` records both the serving model and the requested model

#### Scenario: Routing table is part of the session snapshot

- **WHEN** a session is created with provider, effort, or routing overrides
- **THEN** `session.created` contains that immutable model configuration

#### Scenario: Sidekick handles the mechanical reads

- **WHEN** an interview turn faces a corpus above the delegation threshold
- **THEN** a sidekick call retrieves source-marked spans, the frontier turn receives only those slices, and both calls are journaled
