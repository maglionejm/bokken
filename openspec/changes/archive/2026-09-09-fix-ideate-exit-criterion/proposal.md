# Change: fix-ideate-exit-criterion

## Why

Issue #65: ideate's exit criterion accepts any `decision.recorded` stamped
with the ideate stage. The criteria-freeze decision (question: "convergence
criteria") is journaled in ideate before divergence, so it alone satisfies
the check and the actual convergence decision — which concept advances to
prototype — can be skipped entirely. Observed over MCP: a session left
ideate with frozen criteria and no selected concept.

## What Changes

- Ideate's exit criterion requires the concept-selection decision
  specifically: a decision whose question is
  `which concept advances to prototype`. Stage-scoped governance
  bookkeeping (the criteria freeze) no longer opens the exit.
- The question string becomes a shared constant
  (`CONCEPT_SELECTION_QUESTION` in the orchestrator machine) consumed by
  the ideate engine's emit site and the report context, so the checker and
  the producers cannot drift apart.
- The unmet-criterion message names the missing decision precisely.
- The founder pick prompt drops per-run option event ids (numbered
  summaries only): the strict criterion means ideate really has to reach
  the pick over MCP, and a mailbox port keys answers by question text, so
  the prompt must read the same across resumes to ever be answerable.

## Impact

- Affected specs: `orchestrator` (MODIFIED: Stage entry and exit criteria)
- Affected code: `orchestrator/machine.py`, `orchestrator/__init__.py`,
  `stages/ideate.py`, `report/context.py`, test fakes that emitted a
  non-canonical question and only passed under the lax check, and MCP
  founder-mode test drivers that previously escaped ideate without ever
  making the pick
