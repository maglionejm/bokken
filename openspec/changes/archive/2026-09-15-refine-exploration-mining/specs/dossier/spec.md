# dossier

## MODIFIED Requirements

### Requirement: Part A — Outcomes

Part A SHALL present, concisely: the selected problem statement (with its decision reference), the advanced concept(s), the current-capability map when code exploration ran (one line per capability with its honesty flags: ungrounded, disputed, ratified), the prototype artifacts with their assumption register and per-assumption scores, test results with the kill/iterate/proceed recommendation and its confidence, decisions with owners and dates, and the recommended next loop. Every claim in Part A SHALL carry a ledger reference (event id) resolvable in Part C.

#### Scenario: Outcome claims have receipts

- **WHEN** Part A states the recommendation for a completed session
- **THEN** the statement references the `decision.recorded` event id, and that id resolves in Part C

#### Scenario: In-flight session yields a partial Part A

- **WHEN** a dossier is generated for a session currently in `ideate`
- **THEN** Part A is labeled partial, reports progress through `define`, and omits unreached sections rather than fabricating them

#### Scenario: Capabilities are listed with flags

- **WHEN** a dossier is generated for a session whose journal carries current_capability interpretations, one of them disputed
- **THEN** Part A lists one line per capability and the disputed one is flagged
