# dossier Specification Delta

## MODIFIED Requirements

### Requirement: Journal is the sole input

The Dossier generator SHALL derive all content exclusively from the session's journal (and artifact files referenced by journaled path+hash); it SHALL NOT invoke models, panels, or any source outside the session workspace. Generating a dossier SHALL NOT append events to the journal other than an `artifact.generated` record for the dossier files themselves.

Every payload the generator reads SHALL be obtained as that event type's typed
payload model, not by indexing the raw mapping by string key. This is where
confidence classes and synthetic labels are decided, so a misspelled or renamed
field must surface as an error rather than as a missing value that quietly
downgrades a `simulated` label. Declared-but-untyped extension keys SHALL be
read through their checked accessor, which rejects a name the event type does
not declare.

#### Scenario: Deterministic regeneration

- **WHEN** the dossier is generated twice from the same journal
- **THEN** both outputs are identical apart from the generation timestamp

#### Scenario: No model calls during generation

- **WHEN** a dossier is generated
- **THEN** no `model.called` events are added to the journal

#### Scenario: A journal from an earlier revision still builds a dossier

- **WHEN** the generator is run over a journal written before the typed read
  path existed, carrying undeclared payload keys and a misspelled one
- **THEN** the dossier builds with the same confidence classes, synthetic
  labels, citations, dissent and token usage the records were written with
