# Stages — spec delta (input-aware Empathize)

## MODIFIED Requirements

### Requirement: Empathize engine

The Empathize engine SHALL run an interview program derived from the brief and calibrated to the declared inputs: when discussion/interview material exists, structured behavioral scripts per target segment with laddering follow-ups; when the corpus is chiefly product code, documentation, or metrics, questions those sources can actually answer (what the product does at key moments, what its documentation assumes about users, what the numbers show), with at most one explicitly human-research question per segment whose abstention becomes research debt. In Founder mode the interviewee is the human at the terminal plus optional synthetic panels; in Dojo mode, the cast persona panel. Every answer SHALL be captured as `evidence.captured` with speaker/persona provenance and correct confidence class (`observed`/`reported` for humans, `simulated` for personas); unanswerable questions SHALL be logged as research debt, never papered over. The engine SHALL exit only per the orchestrator's Empathize exit criteria.

#### Scenario: Adaptive follow-up is asked

- **WHEN** an interviewee mentions a recent concrete difficulty
- **THEN** the engine asks a laddering follow-up about that specific instance ("tell me about the last time...") before moving to the next scripted topic

#### Scenario: Founder-mode evidence is not simulated

- **WHEN** the human founder answers an interview question
- **THEN** the evidence event carries `actor.kind: human` and confidence class `observed` or `reported`, never `simulated`

#### Scenario: Gaps become research debt

- **WHEN** the interview program completes with a segment question unanswered by every source
- **THEN** the gap is journaled as research debt and surfaced in session state

#### Scenario: Tangible inputs ground the run

- **WHEN** the brief declares an app repository, metrics files, or discussion transcripts as inputs
- **THEN** the interview program and persona grounding draw on them, and the resulting evidence carries the source kind (`code`, `metrics`, `discussion`) in its citations

#### Scenario: Code-and-docs corpus still yields grounded evidence

- **WHEN** the only inputs are a repository and documents (no discussion transcripts)
- **THEN** the interview program asks predominantly corpus-answerable questions so the stage produces citable evidence, and purely behavioral questions are limited and logged as research debt when personas abstain
