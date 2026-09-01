# panel

## MODIFIED Requirements

### Requirement: Panel casting

Given a session brief (problem space, target segments, risk tolerance) and a requested panel size, the system SHALL cast a panel of personas such that: target segments are covered by sampled demographic/psychographic profiles (documented sampling, not ad-hoc invention); each persona carries personality-variance parameters (OCEAN-style) that measurably vary response style; and the panel always includes three role agents — a skeptic, a feasibility engineer, and a viability/CFO voice — in addition to segment personas. The full casting manifest (per-persona profile, variance parameters, grounding scope, role) SHALL be journaled before the panel produces any content. Segment personas SHALL carry a vivid, deterministic identity derived from the casting seed (given name, age, city, household) so contributions read as concrete people; the identity is role-play flavor only - factual claims still require corpus citations and the simulated confidence class is unchanged.

#### Scenario: Casting covers segments and roles

- **WHEN** a panel of 8 is cast for a brief with two target segments
- **THEN** both segments are represented, the skeptic/feasibility/viability role agents are present, and the journaled manifest documents every persona's profile and variance parameters

#### Scenario: Casting is reproducible from the manifest

- **WHEN** the same brief and a recorded casting seed are used to re-cast
- **THEN** the resulting panel manifest is identical to the journaled one

#### Scenario: Personas are concrete people

- **WHEN** a panel is cast with a fixed seed
- **THEN** each segment persona has a stable name of the form 'Name (age, city)' and the same seed always yields the same identities
