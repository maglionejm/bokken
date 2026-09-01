# Proposal: add-concept-research

## Why

Once a concept is selected, the run knows exactly what to investigate — but
today nothing looks outside the declared corpus. The founder wants a deep,
explicitly authorized internet research pass on the chosen concept, with a
well-structured output that feeds the assumption register, the test lenses,
and the reports.

## What Changes

- After the concept decision, at Prototype entry and before assumption
  enumeration, the engine runs concept research when the brief declares
  `allow_web_research: true`: a research-class call with the provider's
  server-side web search produces deep findings with cited URLs; a second
  structuring call types them into a MarketResearch schema (competitors /
  prior art with overlap, quantified market signals with sources,
  regulatory notes, pricing benchmarks, differentiation risks, open
  questions).
- Findings journal as `reported` evidence with URL sources; artifacts
  `market_research.md` + `market_research.json` (kind `market_research`).
- The assumptions prompt consumes the research; reports gain a "Concept
  research" section. Without the flag, the skip is journaled research debt.
- Router/provider gain a `web_search` request option (single model seam).
- CLI: `bokken new --allow-web-research`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `stages`: Prototype engine gains the concept-research step.
- `models`: web-search-enabled research calls through the router.
- `cli`: the authorization flag.
- `report`: Concept research section.

## Impact

`src/bokken/stages/{research,prototype}.py`, `src/bokken/models/{router,
anthropic_provider,prompts}.py`, `src/bokken/report/*`, CLI, docs + site.
