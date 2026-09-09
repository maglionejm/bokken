# orchestrator

## MODIFIED Requirements

### Requirement: Stage entry and exit criteria

Each stage SHALL declare entry criteria (what must exist in session state to start) and exit criteria (what must exist to leave forward). The orchestrator SHALL evaluate exit criteria against replayed session state, not against in-memory flags. Minimum exit criteria: `intake` — a brief with problem space, constraints, target segments, success criteria, and risk tolerance; `empathize` — at least one evidence event per target segment or an explicit research-debt abstention; `define` — a selected problem statement recorded as a decision with evidence-linked insights; `ideate` — at least one surviving option with the recorded concept-selection decision, the decision whose question is `which concept advances to prototype`; other ideate-stamped decisions, such as the convergence-criteria freeze, SHALL NOT satisfy it; `prototype` — at least one artifact linked to an assumption register; `test` — a scored assumption register and a kill/iterate/proceed recommendation decision.

#### Scenario: Exit blocked until criteria met

- **WHEN** `ideate` is asked to complete while no concept-selection decision exists in the journal
- **THEN** the orchestrator refuses the forward transition and reports which exit criterion is unmet

#### Scenario: Criteria freeze alone does not open ideate's exit

- **WHEN** `ideate` holds a surviving option and the criteria-freeze decision (question `convergence criteria`) but no concept-selection decision
- **THEN** the orchestrator refuses the forward transition, naming the missing concept-selection decision

#### Scenario: Criteria evaluated from replay

- **WHEN** a resumed session is asked to transition
- **THEN** the criteria evaluation uses only journal-derived state, yielding the same verdict as before the interruption
