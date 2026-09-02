# cli

## ADDED Requirements

### Requirement: Run cost framing and receipt

`bokken run` SHALL print, before entering the loop, the session's token
guardrail and the typical full-run cost range; and on halt SHALL print a
receipt computed from journaled model calls — session-to-date list-price
cost in USD and total calls — with a pointer to `bokken costs` for the
per-stage breakdown. In `--as-json` mode the receipt fields SHALL appear in
the result payload.

#### Scenario: Receipt on halt

- **WHEN** a run halts for any reason (gate, budget, completion, stop)
- **THEN** the terminal shows the session-to-date cost and call count derived from the journal

#### Scenario: Framing before spend

- **WHEN** `bokken run` starts on a fresh session
- **THEN** the guardrail and typical cost range are shown before the first model call
