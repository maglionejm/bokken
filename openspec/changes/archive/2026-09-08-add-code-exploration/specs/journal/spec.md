# journal

## ADDED Requirements

### Requirement: Interpretation grounding accepts citations

An `interpretation.derived` record SHALL be considered grounded when it
carries refs to journal events or validated corpus citations (the
`citations` extension key); a record with neither SHALL be rejected unless
it declares `ungrounded: true`.

#### Scenario: Citations ground an interpretation

- **WHEN** an interpretation is appended with validated corpus citations and no refs
- **THEN** the append succeeds with `ungrounded: false`

#### Scenario: Nothing behind it means saying so

- **WHEN** an interpretation is appended with neither refs nor citations and `ungrounded: false`
- **THEN** the append is rejected
