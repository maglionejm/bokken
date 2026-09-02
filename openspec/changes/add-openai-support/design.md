# Design

`OpenAIProvider` implements the existing `Provider` protocol using the OpenAI
Responses API. Structured calls use `responses.parse` with the Pydantic schema;
plain calls use `responses.create`. Usage, request id, model, and incomplete
status are normalized into `ProviderResult`.

The router selects defaults from the session's `config.provider` (`anthropic`
or `openai`). Provider instances are created lazily by an auto provider based
on model family, so importing Bokken and running fake-provider tests never
requires either SDK or an API key. OpenAI models are explicit in the allowlist;
arbitrary model names are rejected as before.

No journal schema changes are needed: `model.called` already records provider-
agnostic model and usage data. `design.md` records the optional dependency
rationale required by the project constitution.
