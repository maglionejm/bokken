# stages Specification

## Purpose
The stages capability defines what each Design Thinking stage actually does when it runs: how evidence is gathered, insights framed, ideas generated and converged, prototypes shaped around assumptions, and tests scored — identically governed in Founder (human-in-the-loop) and Dojo (synthetic panel) modes.

## Requirements

### Requirement: Empathize engine

The Empathize engine SHALL run an interview program derived from the brief and calibrated to the declared inputs: when discussion/interview material exists, structured behavioral scripts per target segment with laddering follow-ups; when the corpus is chiefly product code, documentation, or metrics, questions those sources can actually answer (what the product does at key moments, what its documentation assumes about users, what the numbers show), with at most one explicitly human-research question per segment whose abstention becomes research debt. In Founder mode the interviewee is the human at the terminal plus optional synthetic panels; in Dojo mode, the cast persona panel. Every answer SHALL be captured as `evidence.captured` with speaker/persona provenance and correct confidence class (`observed`/`reported` for humans, `simulated` for personas); unanswerable questions SHALL be logged as research debt, never papered over. In Dojo mode, after interviews complete, the engine SHALL derive desired-outcome statements (JTBD form, each linked to supporting evidence), have every interview persona score each outcome for Importance and Satisfaction (1-10, with a stated reason for extreme scores), and journal a deterministic Opportunity ranking (Opportunity = Importance + max(Importance - Satisfaction, 0), averaged across personas, banded: >=15 severely underserved, 12-15 underserved, <10 served; segment spikes flagged when one persona scores >=17) as `interpretation.derived` records plus an `opportunity_ranking` artifact. The engine SHALL exit only per the orchestrator's Empathize exit criteria. When the brief declares an `app_url`, the engine SHALL — in both modes — additionally perform a functional UI walkthrough before outcome derivation, combining methods: candidate screens SHALL be discovered from the live DOM (every same-origin link, deduplicated by path), from the code itself when a repository input is declared (parameterless GET route definitions and template links, scanning from the repository's version-control root when the declared path is a subdirectory), and — for single-page apps — by activating tab-like controls (`[role=tab]`, navigation buttons) on each visited page and observing the resulting states; the walker SHALL visit the union up to a bounded page budget. For each screen the engine journals the observed facts (title, heading structure, primary actions, forms and their labeling, images without alt text, console errors, load time) as `observed` evidence with source `ui_walkthrough`, captures desktop and mobile screenshots journaled as `ui_screenshot` artifacts, and finally derives a constructive heuristic review journaled as a `ui_review` artifact that states its coverage (screens visited vs discovered). After the crawl, the engine SHALL functionally test the application per feature: a feature inventory (bounded) is derived from the declared documentation, the discovered routes, and the live DOM; for each feature a bounded interaction loop drives the real browser - the model chooses each step (click, fill with demo values, navigate, or conclude) from a digest of the page's interactive elements, destructive controls are never activated, and every step and its observed result are journaled - ending in a per-feature verdict (works / broken / unclear) with an end-state screenshot, exported as `ui_feature_tests` artifacts and consumed by the UI review. When `app_url` is absent or the browser runtime is unavailable, the walkthrough SHALL be skipped as journaled research debt, never silently.

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

#### Scenario: Every feature is exercised, not just inventoried

- **WHEN** a dojo run has a reachable `app_url` and a feature inventory of N features
- **THEN** each feature has journaled interaction steps with observed results, a verdict, and an end-state screenshot, and `ui_feature_tests` artifacts exist

#### Scenario: Destructive controls are never activated

- **WHEN** the interaction loop encounters delete/logout/reset controls
- **THEN** they are excluded from the actionable digest and no such action is executed

#### Scenario: Founder mode also gets the functional test

- **WHEN** a founder-mode session declares a reachable `app_url`
- **THEN** the walkthrough and per-feature tests run and journal observed evidence exactly as in Dojo mode

### Requirement: Define engine

The Define engine SHALL cluster captured evidence into candidate insights (each with `refs` to its supporting evidence; the ungrounded flag when support is missing), draft point-of-view statements and "How Might We" reframes from those insights, score candidate problem statements against evidence coverage, and select the problem statement through a `decision.recorded` IBIS event (question, options, criteria, positions, resolution, dissent). When an opportunity ranking exists, clustering and candidate drafting SHALL consume it, candidate statements SHALL name the affected segment and the underserved outcomes with their scores, and opportunity coverage SHALL be a selection criterion. Rejected framings SHALL be preserved with the reason they lost. A problem statement that embeds a solution SHALL trigger the `hmw_reframe` Kata move before selection can proceed.

#### Scenario: Insight links to its evidence

- **WHEN** clustering produces an insight from three evidence events
- **THEN** the `interpretation.derived` event's `refs` contains those three ids, and the dossier-facing state can resolve them

#### Scenario: Losing framings are preserved

- **WHEN** the problem statement is selected from four candidates
- **THEN** the decision event records all four options and why the losers lost

#### Scenario: Solution-shaped statement is reframed

- **WHEN** a candidate problem statement embeds a specific solution
- **THEN** `hmw_reframe` executes (journaled) and produces a reframed candidate before selection

#### Scenario: Opportunity ranking shapes the statement

- **WHEN** define runs after a dojo Empathize produced an opportunity ranking
- **THEN** the clustering and candidate prompts receive the ranking and the selection decision lists opportunity coverage among its criteria

### Requirement: Ideate engine

The Ideate engine SHALL run divergence then convergence under the pre-frozen criteria. Divergence SHALL enforce per-participant idea quotas, require each idea to state the desired outcome(s) it serves when an outcome ranking exists, separate private reasoning from public contributions for personas (private thoughts are journaled but marked non-public), monitor idea novelty rate, and inject provocation moves (via the Kata) when novelty decays; every idea SHALL enter the lineage graph (`option.created`/`built_on`/`merged`/`split`/`parked`/`killed`) with contributor provenance. Convergence SHALL apply the frozen criteria through recorded votes with voter roles as framework lenses: the feasibility voter SHALL review options adversarially against the repository corpus and state a green/amber/red verdict with a first honest slice and S/M/L effort; the viability voter SHALL score RICE (Reach, Impact, Confidence, Effort) without access to code; the segment voter SHALL score desirability against the outcome ranking. A red feasibility verdict SHALL be recorded as dissent on the selection decision and the option SHALL not win without journaled human override. Convergence SHALL require the skeptic's on-record challenge and produce a `decision.recorded` selecting surviving option(s). The transition from divergence to convergence SHALL occur only via the `timebox_pivot` move (novelty/quota trigger) or an explicit human instruction — both journaled.

#### Scenario: Quotas are enforced in divergence

- **WHEN** divergence runs with a quota of 5 ideas per participant
- **THEN** each participant contributes at least 5 options (or a journaled abstention with reason) before convergence can be proposed

#### Scenario: Novelty decay triggers provocation

- **WHEN** the rate of novel option clusters falls below the configured floor during divergence
- **THEN** a provocation move executes (journaled) before the divergence may pivot

#### Scenario: Idea lineage is complete

- **WHEN** an idea is built on, merged with another, and the merge later killed in convergence
- **THEN** the lineage graph reconstructs the full chain — who seeded, who built, what merged, why killed — from option events alone

#### Scenario: Lenses are firewalled

- **WHEN** convergence votes are collected
- **THEN** the feasibility voter's prompt contains repository excerpts, the viability voter's prompt contains none, and both verdicts land in the vote positions

#### Scenario: Red verdict blocks a silent win

- **WHEN** the feasibility lens returns red for the top-scored option
- **THEN** the selection decision either picks another option or records the red verdict as dissent with an explicit human override

### Requirement: Prototype engine

The Prototype engine SHALL, when the brief declares `allow_web_research: true`, first run concept research on the selected concept: a research-class call with provider-side web search produces deep findings whose sources are cited URLs, a structuring call types them into a MarketResearch record (competitors/prior art with overlap, quantified market signals with sources, regulatory notes, pricing benchmarks, differentiation risks, open questions), findings are journaled as `reported` evidence with their URLs, and `market_research.md` plus `market_research.json` are journaled as `market_research` artifacts. Without the flag the skip SHALL be journaled as research debt. The engine SHALL then build the assumption register, with the research (when present) supplied to assumption enumeration: enumerate the assumptions the selected concept rests on, classify each by risk (impact × uncertainty), and identify the riskiest assumption. Artifact fidelity SHALL be chosen deliberately against that assumption — the cheapest artifact that tests it — and the choice journaled as a decision. The engine SHALL then generate artifacts (MVP kinds: concept one-pager, landing-page copy, storyboard/service blueprint, synthetic demo script) as files in the session workspace, each journaled as `artifact.generated` with `refs` linking it to the assumptions it exercises. A concept one-pager SHALL open with a Hill — Who / What / Wow — followed by a Lean-UX hypothesis ("We believe [outcome] for [segment], measured by [signal]"). Every artifact SHALL map to at least one register entry.

#### Scenario: Riskiest assumption drives fidelity

- **WHEN** the register's riskiest assumption is demand ("would anyone sign up?")
- **THEN** the fidelity decision selects a demand-testing artifact (e.g. landing copy) over a feasibility artifact, with the rationale journaled

#### Scenario: Artifact without assumption is refused

- **WHEN** an artifact generation is attempted with no assumption linkage
- **THEN** the engine refuses and the artifact is not journaled

#### Scenario: One-pager is a Hill

- **WHEN** a concept one-pager artifact is generated
- **THEN** its content opens with Who / What / Wow lines and contains a "We believe" hypothesis with a measurable signal

#### Scenario: Concept research is structured and sourced

- **WHEN** a dojo run with `allow_web_research: true` selects a concept
- **THEN** `market_research` artifacts exist, every market signal carries a source URL, findings are `reported` evidence, and the assumptions prompt received the research

#### Scenario: No web access without authorization

- **WHEN** the brief does not declare `allow_web_research: true`
- **THEN** no web-search call is made and the skip is journaled as research debt

### Requirement: Test engine

The Test engine SHALL evaluate prototype artifacts against the assumption register using, in Dojo mode, a fresh firewalled panel (per the panel capability) and, in Founder mode, a structured read-through with the human plus an optional fresh synthetic panel. Each register entry SHALL be scored (supported / contradicted / untested) with `refs` to the evaluating evidence; the engine SHALL then produce a kill/iterate/proceed recommendation as a `decision.recorded` with a confidence statement quantifying the register (counts per score, which contradictions strike which insight or outcome) and a constructive next-step framing for the founder — including on kill — plus the mandatory `requires_real_validation` flag whenever the evaluation rests on simulated evidence. When results contradict an earlier insight or the problem statement, the engine SHALL propose the corresponding loop-back (via the `loopback_proposal` move) citing the contradicting evidence; loop-backs execute only through the orchestrator's transition rules.

#### Scenario: Assumptions are scored with evidence

- **WHEN** the test run completes
- **THEN** every assumption-register entry has a journaled score with refs to evaluation evidence, and untested entries are explicitly `untested`, not omitted

#### Scenario: Contradiction proposes a loop-back

- **WHEN** panel evaluation contradicts the insight underlying the problem statement
- **THEN** a `loopback_proposal` move executes citing the contradicting evidence ids, proposing `test → define`

#### Scenario: Simulated-only test cannot claim validation

- **WHEN** the recommendation rests solely on synthetic panel evidence
- **THEN** the recommendation decision carries `requires_real_validation` and its rendered form states that validation with real users is pending

### Requirement: Stage engines honor mode parity

Each engine SHALL implement the same stage contract in both modes, sourcing participation through the orchestrator's input port and panel interfaces only, so that mode changes never alter the event families produced, the criteria evaluated, or the governance rules applied.

#### Scenario: Same engine, both modes

- **WHEN** the Define engine runs in Founder mode and in Dojo mode on equivalent evidence
- **THEN** both runs produce the same event families (interpretations, decisions with dissent) and differ only in actor provenance and confidence classes
