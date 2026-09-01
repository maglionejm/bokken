# models

## ADDED Requirements

### Requirement: Web-search-enabled research calls

The router SHALL accept a per-invocation `web_search` option that the
provider maps to its server-side web search tool; it SHALL be honored only
for `research`-class calls, and the resulting `model.called` event SHALL
record that web search was enabled. The fake provider SHALL accept the
option so tests run offline.

#### Scenario: Web search reaches the provider request

- **WHEN** a research-class call is invoked with `web_search=True`
- **THEN** the provider request includes the server-side web search tool and the journaled call records `web_search: true`

#### Scenario: Non-research classes cannot search

- **WHEN** a cognition-class call passes `web_search=True`
- **THEN** the router rejects the invocation with a typed error
