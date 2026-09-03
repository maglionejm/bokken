# models Specification Delta

## ADDED Requirements

### Requirement: Attribution derives from the completed call

Journaled agent provenance SHALL name the model that **answered** the call
that produced the contribution, never the model routing requested for its
lane. The two differ for a configured, expected reason — the Fable classes
carry a server-side fallback to `claude-opus-4-8` — and when they do, an actor
stamped from the routing table contradicts the `model.called` record for the
same contribution. Two records disagreeing about one contribution SHALL never
be possible.

The seam SHALL make the served model reachable by the caller that journals the
contribution: a completed invocation SHALL expose an attribution carrying the
served model, the shared structured-output helper SHALL return the validated
payload together with that attribution as one value, and the actor SHALL be
built from the attribution rather than from a model string paired with the
payload by hand. There SHALL NOT be a second, parallel helper that returns the
payload without its provenance.

Personas SHALL contribute their identity (name and `persona_id`) to an actor
and the completed call SHALL contribute the model; a persona SHALL NOT accept a
bare model string, since which model spoke is unknowable until the call has
answered. Stage, panel, and kata code SHALL NOT read the routing table to build
an actor.

A contribution that no single model call produced — a facilitation move, a
deterministic tally, a file the harness rendered from records already on the
ledger, a governance refusal dispatched no call — SHALL claim no model at all.
An actor with no model is silent; an actor naming a model that did not do the
work is false, and the honesty rules prefer silence. The router SHALL therefore
claim no model when asked for an actor, because before a call returns it knows
only what it asked for.

The offline test suite SHALL include a fake provider that answers on a
different model than it was asked for, so that requested and served are
distinguishable in tests, and SHALL assert that every agent-attributed record
of a full run names a model that was actually served and none that was only
requested. A fake that echoes the requested model back SHALL NOT be the only
provider the provenance assertions run against.

#### Scenario: A server-side fallback does not falsify the ledger

- **WHEN** a research-class call is answered by the fallback model rather than the requested one
- **THEN** the contributions journaled from that call carry the served model in `actor.model`, matching the `model.called` record's `model` and differing from its `requested_model`

#### Scenario: The payload cannot be separated from its provenance

- **WHEN** an engine obtains a schema-validated payload through the structured-output helper
- **THEN** it receives the payload and the producing call's attribution as one value, and building an actor from it requires no knowledge of the routing table

#### Scenario: A persona names the model that spoke

- **WHEN** a persona utterance, evaluation, or outcome score is journaled
- **THEN** the actor carries the persona's `persona_id` with the served model of the call that produced that turn, and persona evidence keeps `confidence_class: simulated`

#### Scenario: Work no call produced claims no model

- **WHEN** a facilitation move, a deterministic opportunity or vote tally, or a governance refusal that dispatched no call is journaled
- **THEN** the record's actor carries no model rather than the model routing would have used

#### Scenario: The router refuses to attribute

- **WHEN** an actor is requested from the router for a routing class
- **THEN** the returned actor carries no model, because the served model is not yet knowable

#### Scenario: The guard sees a divergence

- **WHEN** a full offline run executes against a provider that serves every lane on a different model than requested
- **THEN** the set of models named by agent actors is a subset of the served models and disjoint from the requested-only models, and each Test-stage persona reaction names the server of the evaluation call that produced it

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
the call alongside the model routing requested; journaled agent provenance
SHALL follow the served model per the attribution requirement, never the
routing table.

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

- **WHEN** an OpenAI session journals facilitator, persona, researcher, or tester contributions, including calls answered by a fallback model
- **THEN** every actor's model belongs to the OpenAI provider and is one the session actually had served, and `model.called` records both the serving model and the requested model

#### Scenario: Routing table is part of the session snapshot

- **WHEN** a session is created with provider, effort, or routing overrides
- **THEN** `session.created` contains that immutable model configuration

#### Scenario: Sidekick handles the mechanical reads

- **WHEN** an interview turn faces a corpus above the delegation threshold
- **THEN** a sidekick call retrieves source-marked spans, the frontier turn receives only those slices, and both calls are journaled
