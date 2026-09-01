# library

## ADDED Requirements

### Requirement: Learnings compound across runs

Finalization SHALL append one summary record per completed session to a
workspace-level library (session name, product key, verdict, scored
assumptions, top opportunities, broken UI findings), idempotently. New runs
on the same product SHALL receive a prior-learnings digest in the research
program prompt - marked with the originating session names so borrowed
learnings are never laundered into fresh evidence - and the interviewer is
instructed not to re-ask what is settled and to probe what was contradicted.

#### Scenario: The second run knows what the first learned

- **WHEN** a session on a product finalizes and a new session starts on the same product
- **THEN** the new session's interview-program prompt contains the prior session's supported/contradicted learnings with its session name

#### Scenario: Library is idempotent and product-scoped

- **WHEN** finalization runs twice and another product queries the library
- **THEN** exactly one record exists for the session and the other product sees none of it
