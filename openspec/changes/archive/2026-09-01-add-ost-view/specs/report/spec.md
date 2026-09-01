# report

## ADDED Requirements

### Requirement: Opportunity Solution Tree view

The HTML report SHALL include an Opportunity Solution Tree chapter derived
from the journal graph — the framed outcome at the root, the Ulwick-ranked
opportunities beneath it, the advanced solution under each, and its
assumption tests with their scores — rendered as a collapsible tree; the
section states honestly when no ranking was journaled.

#### Scenario: The tree reads from the journal

- **WHEN** a session with an opportunity ranking is exported
- **THEN** the HTML shows outcome, opportunities, solution, and scored assumption tests as nested, collapsible nodes
