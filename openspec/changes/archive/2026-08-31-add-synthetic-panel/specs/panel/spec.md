# Panel — spec delta

## Purpose

The panel capability provides governed synthetic participants: personas cast from the brief with controlled diversity, grounded in an explicit evidence corpus with abstention, structurally protected against sycophancy, and firewalled so that no panel evaluates work it helped create. Its outputs are simulations — labeled as such everywhere, always.

## ADDED Requirements

### Requirement: Panel casting

Given a session brief (problem space, target segments, risk tolerance) and a requested panel size, the system SHALL cast a panel of personas such that: target segments are covered by sampled demographic/psychographic profiles (documented sampling, not ad-hoc invention); each persona carries personality-variance parameters (OCEAN-style) that measurably vary response style; and the panel always includes three role agents — a skeptic, a feasibility engineer, and a viability/CFO voice — in addition to segment personas. The full casting manifest (per-persona profile, variance parameters, grounding scope, role) SHALL be journaled before the panel produces any content.

#### Scenario: Casting covers segments and roles

- **WHEN** a panel of 8 is cast for a brief with two target segments
- **THEN** both segments are represented, the skeptic/feasibility/viability role agents are present, and the journaled manifest documents every persona's profile and variance parameters

#### Scenario: Casting is reproducible from the manifest

- **WHEN** the same brief and a recorded casting seed are used to re-cast
- **THEN** the resulting panel manifest is identical to the journaled one

### Requirement: Evidence grounding with abstention

Personas SHALL answer factual questions only from the session's ingested evidence corpus, citing the supporting span(s) (source id + location) in each answer; when the corpus does not support an answer, the persona SHALL abstain rather than invent. Every abstention SHALL be journaled as `evidence.abstained` (research debt) naming the unanswerable question and the gap. Opinion/preference responses generated from the persona profile (not the corpus) SHALL be marked as profile-derived, distinct from corpus-grounded content. All persona contributions SHALL carry `confidence_class: simulated`.

#### Scenario: Grounded answer cites its span

- **WHEN** a persona answers a question the corpus supports
- **THEN** the journaled evidence event includes at least one citation resolvable to a corpus span, and `confidence_class` is `simulated`

#### Scenario: Ungrounded question produces abstention, not invention

- **WHEN** a persona is asked a factual question the corpus cannot support
- **THEN** the persona abstains, an `evidence.abstained` event records the question and gap, and no fabricated answer enters the record

#### Scenario: Research debt is enumerable

- **WHEN** the session state is queried after an Empathize run
- **THEN** all abstentions are listed as research debt items available to the Dossier

### Requirement: Contamination firewall

A panel that participated in `ideate` or `prototype` for a session SHALL never evaluate that session's prototype in `test`. Test-stage panels SHALL be freshly cast with zero persona overlap (verified against journaled manifests), and the firewall check SHALL run and be journaled before any Test-stage evaluation begins; a violation attempt SHALL abort the Test run.

#### Scenario: Fresh test panel is enforced

- **WHEN** `test` begins for a session whose ideation panel is journaled
- **THEN** the test panel manifest shares no persona with the ideation manifest and a journaled firewall check records the disjointness verification

#### Scenario: Overlap aborts the evaluation

- **WHEN** a test evaluation is attempted with a panel containing any persona from the ideation manifest
- **THEN** the evaluation is refused before any persona sees the prototype, and the refusal is journaled

### Requirement: Anti-sycophancy structure

The system SHALL ensure personas are never shown the sponsor's preferred answer, hypothesis framing marked as preferred, or any signal of desired outcome; prompts rendered to personas SHALL be constructed from the neutral brief and stage materials only. The skeptic role SHALL hold a protected contribution quota that cannot be reduced by configuration below one intervention per convergence decision. Convergence criteria (e.g. Desirability–Feasibility–Viability weights) SHALL be fixed and journaled before divergence begins and SHALL be immutable for the remainder of the run.

#### Scenario: Preferred answer never reaches personas

- **WHEN** the brief contains a sponsor hypothesis annotated as preferred
- **THEN** the material rendered to any persona excludes the preference marking, verifiable from journaled prompt identifiers

#### Scenario: Criteria fixed before ideation

- **WHEN** divergence starts in `ideate`
- **THEN** a journaled criteria event predates all option events, and later attempts to alter criteria are refused and journaled

#### Scenario: Skeptic quota is protected

- **WHEN** a convergence decision is being prepared
- **THEN** the skeptic has contributed at least one on-record challenge, or the convergence is blocked until it exists

### Requirement: Simulation labeling and validation flags

Every panel output surfaced anywhere (journal, state, dossier, CLI, MCP) SHALL be labeled as synthetic/simulated at the record level. Any decision whose supporting evidence is wholly or partly `simulated` or `assumed` SHALL carry a `requires_real_validation` flag that propagates to session state and the Dossier; the system SHALL provide no configuration to disable this labeling.

#### Scenario: Labels survive derivation

- **WHEN** an insight is derived solely from synthetic interview answers
- **THEN** the insight's grounding shows `simulated` confidence and any decision resting on it carries `requires_real_validation`

#### Scenario: Labeling cannot be turned off

- **WHEN** any configuration attempts to suppress synthetic labeling
- **THEN** the configuration is rejected as invalid
