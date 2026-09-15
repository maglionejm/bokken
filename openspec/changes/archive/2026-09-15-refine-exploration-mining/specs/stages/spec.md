# stages

## MODIFIED Requirements

### Requirement: Code exploration

When a session's corpus contains code sources, Empathize SHALL open by
mapping the product's current capabilities - actor, trigger, observable
outcome - from the code corpus via one cognition-lane call, validating every
citation against the corpus and journaling each capability as an
`interpretation.derived` of kind `current_capability` (ungrounded when no
citation survives validation). Each validated citation SHALL carry, inside
the `citations` extension key, a deterministic verbatim quote of its resolved
corpus span truncated to at most 200 characters - the label stays "cited",
never "proven". The same call SHALL also ask for the product's own
vocabulary: up to 10 domain terms with meanings and citations, each
journaled as an `interpretation.derived` of kind `domain_term` with
citations validated (and quoted) the same way. A rendered glossary SHALL be
threaded into the `define/cluster` and `handoff/specify` prompts, reading
"(no glossary)" when no terms are on file. The map SHALL feed the feature
inventory of the UI walkthrough. Sessions without code sources SHALL skip
exploration without a model call.

In founder mode only, the engine SHALL ask the founder per capability - one
compact prompt accepting confirm / dispute / skip (c/d/s) - through the
session's input port, letting `InputRequired` propagate like every other
founder ask. A confirmation marks the capability interpretation with the
declared extension key `ratified: true`; a dispute marks it
`ratified: false` and appends the founder's correction as `evidence.captured`
(human, `reported`) ref'ing the interpretation; a skip journals nothing
extra. Dojo runs SHALL be unchanged.

#### Scenario: Implemented behavior is mapped and cited

- **WHEN** a dojo run starts with a repo input
- **THEN** the journal carries current_capability interpretations whose citations resolve to real corpus spans, before any persona is interviewed

#### Scenario: No code, no spend

- **WHEN** a session has only metrics and discussion inputs
- **THEN** exploration makes no model call and the run proceeds unchanged

#### Scenario: Citations carry readable quotes

- **WHEN** a capability's citation survives validation
- **THEN** its journaled citation dict carries a `quote` of the resolved span text, truncated to at most 200 characters, produced without any model call

#### Scenario: The founder confirms a capability

- **WHEN** a founder-mode run maps a capability and the founder answers "c"
- **THEN** the capability interpretation carries `ratified: true`

#### Scenario: The founder disputes a capability

- **WHEN** the founder answers "d" with a correction
- **THEN** the interpretation carries `ratified: false` and the correction is journaled as human `reported` evidence ref'ing that interpretation

#### Scenario: A skip leaves no trace

- **WHEN** the founder answers "s"
- **THEN** no ratification key and no evidence is journaled for that capability

#### Scenario: Dojo runs never ratify

- **WHEN** a dojo run maps capabilities
- **THEN** no ratification prompt is issued and no `ratified` key is journaled

#### Scenario: Domain terms are journaled with citations

- **WHEN** the capability map returns glossary terms citing the code corpus
- **THEN** each term is journaled as an `interpretation.derived` of kind `domain_term` with validated, quoted citations

#### Scenario: The glossary reaches downstream prompts

- **WHEN** define/cluster and handoff/specify render on a session with journaled domain terms
- **THEN** their rendered prompts carry the glossary, and "(no glossary)" when the session has none
