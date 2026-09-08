# stages

## ADDED Requirements

### Requirement: Code exploration

When a session's corpus contains code sources, Empathize SHALL open by
mapping the product's current capabilities - actor, trigger, observable
outcome - from the code corpus via one cognition-lane call, validating every
citation against the corpus and journaling each capability as an
`interpretation.derived` of kind `current_capability` (ungrounded when no
citation survives validation). The map SHALL feed the feature inventory of
the UI walkthrough. Sessions without code sources SHALL skip exploration
without a model call.

#### Scenario: Implemented behavior is mapped and cited

- **WHEN** a dojo run starts with a repo input
- **THEN** the journal carries current_capability interpretations whose citations resolve to real corpus spans, before any persona is interviewed

#### Scenario: No code, no spend

- **WHEN** a session has only metrics and discussion inputs
- **THEN** exploration makes no model call and the run proceeds unchanged
