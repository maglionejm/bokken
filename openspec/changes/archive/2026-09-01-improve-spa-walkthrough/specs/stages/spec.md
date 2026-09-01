# stages

## MODIFIED Requirements

### Requirement: Empathize engine

The Empathize engine SHALL run an interview program derived from the brief and calibrated to the declared inputs: when discussion/interview material exists, structured behavioral scripts per target segment with laddering follow-ups; when the corpus is chiefly product code, documentation, or metrics, questions those sources can actually answer (what the product does at key moments, what its documentation assumes about users, what the numbers show), with at most one explicitly human-research question per segment whose abstention becomes research debt. In Founder mode the interviewee is the human at the terminal plus optional synthetic panels; in Dojo mode, the cast persona panel. Every answer SHALL be captured as `evidence.captured` with speaker/persona provenance and correct confidence class (`observed`/`reported` for humans, `simulated` for personas); unanswerable questions SHALL be logged as research debt, never papered over. In Dojo mode, after interviews complete, the engine SHALL derive desired-outcome statements (JTBD form, each linked to supporting evidence), have every interview persona score each outcome for Importance and Satisfaction (1-10, with a stated reason for extreme scores), and journal a deterministic Opportunity ranking (Opportunity = Importance + max(Importance - Satisfaction, 0), averaged across personas, banded: >=15 severely underserved, 12-15 underserved, <10 served; segment spikes flagged when one persona scores >=17) as `interpretation.derived` records plus an `opportunity_ranking` artifact. The engine SHALL exit only per the orchestrator's Empathize exit criteria. When the brief declares an `app_url`, the Dojo engine SHALL additionally perform a functional UI walkthrough before outcome derivation, combining methods: candidate screens SHALL be discovered from the live DOM (every same-origin link, deduplicated by path), from the code itself when a repository input is declared (parameterless GET route definitions and template links, scanning from the repository's version-control root when the declared path is a subdirectory), and — for single-page apps — by activating tab-like controls (`[role=tab]`, navigation buttons) on each visited page and observing the resulting states; the walker SHALL visit the union up to a bounded page budget. For each screen the engine journals the observed facts (title, heading structure, primary actions, forms and their labeling, images without alt text, console errors, load time) as `observed` evidence with source `ui_walkthrough`, captures desktop and mobile screenshots journaled as `ui_screenshot` artifacts, and finally derives a constructive heuristic review journaled as a `ui_review` artifact that states its coverage (screens visited vs discovered). When `app_url` is absent or the browser runtime is unavailable, the walkthrough SHALL be skipped as journaled research debt, never silently.

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

#### Scenario: Opportunity ranking is journaled

- **WHEN** a dojo Empathize stage completes its interviews
- **THEN** desired outcomes exist as `interpretation.derived` records with evidence refs, every outcome has per-persona Importance/Satisfaction scores, each outcome has an `opportunity` record with its computed score and band, and an `opportunity_ranking` artifact is journaled

#### Scenario: UI walkthrough is documented evidence

- **WHEN** a dojo session is created with `app_url` pointing at a reachable instance
- **THEN** per-screen observations are journaled as `observed` evidence with source `ui_walkthrough`, screenshots exist as `ui_screenshot` artifacts, and a `ui_review` artifact is journaled

#### Scenario: Missing app is honest debt

- **WHEN** no `app_url` is declared or the browser runtime is unavailable
- **THEN** the walkthrough is journaled as research debt (an abstention naming the gap) and the run continues

#### Scenario: Coverage beyond the home page

- **WHEN** the app exposes several same-origin routes via its DOM or its route definitions
- **THEN** the walkthrough visits multiple distinct paths (up to the page budget), not just the entry page, and the review states visited-vs-discovered coverage

#### Scenario: Single-page tabs are exercised

- **WHEN** a visited page exposes tab-like controls instead of links
- **THEN** the walker activates them (bounded), captures each resulting state as its own observation with a screenshot, and the review covers those states
