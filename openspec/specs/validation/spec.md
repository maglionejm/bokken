# validation Specification

## Purpose
Validation closes the loop the synthetic run opened: a deterministic interview guide from the research debt and untested assumptions, an agentic interviewer that moderates real humans over a channel port, and rescoring that confronts the register with reported evidence — so requires_real_validation can finally clear on the strength of real people, never simulation.

## Requirements

### Requirement: Interview guide from the journal

The guide SHALL be derived deterministically from the session's research
debt and untested assumptions — one section per theme with the debt
questions verbatim and one falsifiable probe per untested assumption — and
journaled as a `validation_guide` artifact before any interview starts.

#### Scenario: Guide covers the debt

- **WHEN** a session has journaled research debt and untested assumptions
- **THEN** the guide artifact contains every unique debt question and one probe per untested assumption

### Requirement: Agentic interviewer over a channel port

The interviewer SHALL run as a bounded turn loop on the research class:
given the guide and the transcript so far it chooses ask / follow-up /
conclude; the Channel port delivers questions and returns real answers.
Every exchange SHALL journal as `evidence.captured` with
`confidence_class: reported` and participant provenance
(`actor.kind: human`); the interviewer never invents answers and concludes
within the configured turn budget.

#### Scenario: Real answers are human evidence

- **WHEN** a participant answers over any channel
- **THEN** the journaled evidence carries actor.kind human, the participant label, and confidence reported — never simulated

### Requirement: Rescoring after real evidence

After an interview the engine SHALL rescore the untested assumptions
against the real evidence via a challenge-class call, journaling
`assumption.scored` with refs to the reported evidence; regenerated reports
SHALL show the synthetic-vs-real register delta in a "Real validation"
section.

#### Scenario: The flag can finally clear

- **WHEN** rescoring supports an assumption with reported evidence
- **THEN** the register shows the new score with refs resolving to the real exchanges
