# Add OpenAI model support

Bokken currently hard-wires the Anthropic SDK at its runtime wiring seam. This
change adds OpenAI as a second provider without changing stage engines or the
Journal contract (Blueprint §5: the model router is the single provider seam).

Users may select OpenAI for a session; calls remain routed, validated, and
journaled exactly like Anthropic calls. The OpenAI SDK remains optional so core
installs and offline tests stay lightweight.

## Scope

- Add an optional `openai` dependency and a Responses API provider.
- Add supported OpenAI model identifiers and provider-aware default routing.
- Add CLI/MCP session selection and document setup.
- Preserve lazy SDK imports and fake-provider testability.
