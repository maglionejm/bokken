# report

## ADDED Requirements

### Requirement: Concept research section

When `market_research` artifacts exist, both report formats SHALL include a
"Concept research" section presenting the structured findings — competitors
and prior art with overlap, market signals with their source URLs,
regulatory notes, pricing benchmarks, differentiation risks, and open
questions. When research was skipped, the journaled skip remains visible in
the research-debt listing.

#### Scenario: Research reaches the reports

- **WHEN** a session with concept research is exported
- **THEN** the HTML and the deck contain the Concept research section with sourced signals
