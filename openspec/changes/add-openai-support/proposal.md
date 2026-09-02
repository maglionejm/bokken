# Proposal: add-openai-support

## Why

Bokken's model router is intentionally the single LLM seam, but production
wiring currently supports only Anthropic. Users with OpenAI projects need the
same routed, budgeted, structured, and journaled execution without weakening
Fusion lane economics or making another SDK mandatory (Blueprint §5).

## What Changes

- Add an optional OpenAI Responses API adapter with structured outputs, web
  search, streaming completion handling, implicit prompt-cache compatibility,
  and normalized usage metadata.
- Add explicit provider selection and provider-specific routing defaults.
- Allow one model override for frontier lanes only; keep delegated sidekick and
  extraction work on economical provider defaults.
- Apply configurable `low | medium | high` reasoning effort for both providers.
- Add OpenAI list prices to deterministic cost reports.
- Expose provider/model/effort selection through CLI and MCP session creation.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: provider-aware routing and an optional OpenAI adapter behind the
  existing model seam.

## Impact

`src/bokken/models/`, CLI and MCP creation adapters, report pricing,
documentation, tests, `pyproject.toml`, and `uv.lock`.
