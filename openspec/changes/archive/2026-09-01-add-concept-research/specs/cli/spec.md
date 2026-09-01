# cli

## ADDED Requirements

### Requirement: Web research authorization flag

`bokken new --allow-web-research` SHALL set `allow_web_research: true` on
the brief; without it the flag defaults to false. The setting SHALL be
visible in the journaled config/brief snapshot.

#### Scenario: Flag lands in the brief

- **WHEN** `bokken new x --brief b.json --allow-web-research` is invoked
- **THEN** the journaled brief carries `allow_web_research: true`
