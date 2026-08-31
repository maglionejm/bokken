# Stages — spec delta

## Purpose

The stages capability defines what each Design Thinking stage actually does when it runs: how evidence is gathered, insights framed, ideas generated and converged, prototypes shaped around assumptions, and tests scored — identically governed in Founder (human-in-the-loop) and Dojo (synthetic panel) modes.

## ADDED Requirements

### Requirement: Empathize engine

The Empathize engine SHALL run an interview program derived from the brief: structured interview scripts per target segment that adapt follow-ups to prior answers (laddering). In Founder mode the interviewee is the human at the terminal plus optional synthetic panels; in Dojo mode, the cast persona panel. Every answer SHALL be captured as `evidence.captured` with speaker/persona provenance and correct confidence class (`observed`/`reported` for humans, `simulated` for personas); unanswerable questions SHALL be logged as research debt, never papered over. The engine SHALL exit only per the orchestrator's Empathize exit criteria.

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

### Requirement: Define engine

The Define engine SHALL cluster captured evidence into candidate insights (each with `refs` to its supporting evidence; the ungrounded flag when support is missing), draft point-of-view statements and "How Might We" reframes from those insights, score candidate problem statements against evidence coverage, and select the problem statement through a `decision.recorded` IBIS event (question, options, criteria, positions, resolution, dissent). Rejected framings SHALL be preserved with the reason they lost. A problem statement that embeds a solution SHALL trigger the `hmw_reframe` Kata move before selection can proceed.

#### Scenario: Insight links to its evidence

- **WHEN** clustering produces an insight from three evidence events
- **THEN** the `interpretation.derived` event's `refs` contains those three ids, and the dossier-facing state can resolve them

#### Scenario: Losing framings are preserved

- **WHEN** the problem statement is selected from four candidates
- **THEN** the decision event records all four options and why the losers lost

#### Scenario: Solution-shaped statement is reframed

- **WHEN** a candidate problem statement embeds a specific solution
- **THEN** `hmw_reframe` executes (journaled) and produces a reframed candidate before selection

### Requirement: Ideate engine

The Ideate engine SHALL run divergence then convergence under the pre-frozen criteria. Divergence SHALL enforce per-participant idea quotas, separate private reasoning from public contributions for personas (private thoughts are journaled but marked non-public), monitor idea novelty rate, and inject provocation moves (via the Kata) when novelty decays; every idea SHALL enter the lineage graph (`option.created`/`built_on`/`merged`/`split`/`parked`/`killed`) with contributor provenance. Convergence SHALL apply the frozen criteria through recorded votes with voter roles, require the skeptic's on-record challenge, and produce a `decision.recorded` selecting surviving option(s). The transition from divergence to convergence SHALL occur only via the `timebox_pivot` move (novelty/quota trigger) or an explicit human instruction — both journaled.

#### Scenario: Quotas are enforced in divergence

- **WHEN** divergence runs with a quota of 5 ideas per participant
- **THEN** each participant contributes at least 5 options (or a journaled abstention with reason) before convergence can be proposed

#### Scenario: Novelty decay triggers provocation

- **WHEN** the rate of novel option clusters falls below the configured floor during divergence
- **THEN** a provocation move executes (journaled) before the divergence may pivot

#### Scenario: Idea lineage is complete

- **WHEN** an idea is built on, merged with another, and the merge later killed in convergence
- **THEN** the lineage graph reconstructs the full chain — who seeded, who built, what merged, why killed — from option events alone

### Requirement: Prototype engine

The Prototype engine SHALL first build the assumption register: enumerate the assumptions the selected concept rests on, classify each by risk (impact × uncertainty), and identify the riskiest assumption. Artifact fidelity SHALL be chosen deliberately against that assumption — the cheapest artifact that tests it — and the choice journaled as a decision. The engine SHALL then generate artifacts (MVP kinds: concept one-pager, landing-page copy, storyboard/service blueprint, synthetic demo script) as files in the session workspace, each journaled as `artifact.generated` with `refs` linking it to the assumptions it exercises. Every artifact SHALL map to at least one register entry.

#### Scenario: Riskiest assumption drives fidelity

- **WHEN** the register's riskiest assumption is demand ("would anyone sign up?")
- **THEN** the fidelity decision selects a demand-testing artifact (e.g. landing copy) over a feasibility artifact, with the rationale journaled

#### Scenario: Artifact without assumption is refused

- **WHEN** an artifact generation is attempted with no assumption linkage
- **THEN** the engine refuses and the artifact is not journaled

### Requirement: Test engine

The Test engine SHALL evaluate prototype artifacts against the assumption register using, in Dojo mode, a fresh firewalled panel (per the panel capability) and, in Founder mode, a structured read-through with the human plus an optional fresh synthetic panel. Each register entry SHALL be scored (supported / contradicted / untested) with `refs` to the evaluating evidence; the engine SHALL then produce a kill/iterate/proceed recommendation as a `decision.recorded` with a confidence statement and mandatory `requires_real_validation` flag whenever the evaluation rests on simulated evidence. When results contradict an earlier insight or the problem statement, the engine SHALL propose the corresponding loop-back (via the `loopback_proposal` move) citing the contradicting evidence; loop-backs execute only through the orchestrator's transition rules.

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
