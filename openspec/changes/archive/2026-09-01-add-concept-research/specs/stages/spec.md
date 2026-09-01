# stages

## MODIFIED Requirements

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
