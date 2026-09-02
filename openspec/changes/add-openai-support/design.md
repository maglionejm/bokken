# Design

## Provider adapter

`OpenAIProvider` implements the existing `Provider` protocol with the official
OpenAI SDK's Responses API. Structured calls use `responses.parse` with the
Pydantic schema; plain calls use `responses.create`. Usage, response id, model,
and incomplete status are normalized into `ProviderResult`.

The SDK is an optional `[openai]` dependency and imported only when an OpenAI
model is dispatched. This dependency is justified because the official SDK
owns Responses API transport, typed structured-output parsing, streaming, and
credential/base-URL behavior; core and fake-provider installs do not need it.

## Routing and effort

The journaled session config selects `anthropic` or `openai`. A model-to-provider
registry drives lazy adapter selection and rejects cross-provider routing.
Provider defaults preserve the Fusion boundary: OpenAI uses `gpt-5` on frontier
lanes and `gpt-5-mini` on sidekick/extraction; `--model` overrides only the four
frontier lanes. Both adapters apply the configured reasoning effort rather than
silently ignoring it.

OpenAI model identifiers are documented in the official model registry and
individual model pages:

- https://platform.openai.com/docs/models
- https://platform.openai.com/docs/models/gpt-5.6-luna
- https://platform.openai.com/docs/models/gpt-5.6-terra
- https://platform.openai.com/docs/models/gpt-5.6-sol

List-price estimates come from each official model page. Because OpenAI reports
cached tokens inside total input tokens, the adapter normalizes input and cache
read into disjoint buckets before the existing cost model applies cached-input
rates.

## Prompt caching and tools

Anthropic's internal `<<<CACHE>>>` marker creates explicit cache-control blocks.
OpenAI caches repeated prefixes implicitly, so its adapter removes the marker
while preserving prefix-before-suffix ordering. Hosted search uses the current
Responses API `web_search` tool documented at:
https://platform.openai.com/docs/guides/tools-web-search. (The same page marks
`web_search_preview` as the legacy tool name.)

No Journal schema change is needed: `model.called` already records
provider-neutral model, request, status, and usage fields.
