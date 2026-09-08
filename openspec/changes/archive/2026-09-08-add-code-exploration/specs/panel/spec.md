# panel

## ADDED Requirements

### Requirement: Evidence roles in context

Corpus context rendering SHALL declare, in each source block header, what
that source kind can establish (code: implemented behavior, not desired
intent; metrics: measured current behavior; discussion: reported human
intent; document: stated intent that may omit failure modes), so every
prompt consuming the corpus inherits the same evidence epistemology.

#### Scenario: A persona cannot mistake code for intent

- **WHEN** the corpus context is rendered for any consumer
- **THEN** each source block header carries its kind's evidence role
