# Tasks

- [x] Add provider-aware routing and OpenAI model allowlist; verified with router tests.
- [x] Implement lazy OpenAI Responses provider; verified with stub-client contract tests.
- [x] Preserve cache-marker semantics and Fusion lane economics; verified with provider and routing tests.
- [x] Apply reasoning effort to both providers and add explicit OpenAI prices; verified with provider and report tests.
- [x] Wire CLI/MCP session selection and update documentation; verified with `make check`.
- [x] Derive allowlist, provider map, and prices from one model registry with frontier/reasoning capability guards; verified with routing and price-coverage tests.
- [x] Normalize OpenAI refusal, truncation, and failure statuses, and stream structured generations; verified with stub-client tests.
- [x] Refuse unavailable providers before journaling and derive agent provenance from session routing; verified with auto-provider and end-to-end tests.
