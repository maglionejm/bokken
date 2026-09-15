# report

## ADDED Requirements

### Requirement: Current-capability map in deliverables

When the journal carries `current_capability` interpretations, the HTML
report SHALL render a "What the product does today" block in the inputs
chapter: one entry per capability with its statement, its citation quotes,
and honest flags - `(ungrounded)` when no citation survived validation and
`(disputed by founder)` when the founder disputed it. Ratified capabilities
MAY be marked as founder-confirmed. The block SHALL be a deterministic
rendering of the journal with no model calls, and sessions without
capability interpretations SHALL omit it.

#### Scenario: The map is surfaced with quotes and flags

- **WHEN** a session with cited, ungrounded, and disputed capabilities is exported
- **THEN** the HTML contains the "What the product does today" block with each statement, at least one citation quote, and the `(ungrounded)` and `(disputed by founder)` flags on the right entries

#### Scenario: No capabilities, no block

- **WHEN** a session that never ran code exploration is exported
- **THEN** the HTML contains no "What the product does today" block
