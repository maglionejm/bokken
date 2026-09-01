# Tasks: add-concept-research

## 1. Model seam

- [x] 1.1 Router `web_search` option (research-only, journaled) + provider
  server-side web_search tool + fake provider passthrough; verify with
  contract tests

## 2. Stage step

- [x] 2.1 `stages/research.py`: two-phase concept research (deep call +
  structuring into MarketResearch schema), journaling (reported evidence,
  md+json artifacts), skip-as-debt; wire into Prototype before assumptions;
  assumptions prompt v3 consumes research; verify offline e2e both paths

## 3. Surfaces

- [x] 3.1 CLI --allow-web-research; report+deck Concept research section;
  docs + GitHub page pass; verify report tests and rendered QA
