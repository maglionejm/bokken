# Design: add-synthetic-panel

## Context

See proposal.md. Constraints: the panel engine must be a separate module from facilitation cognition (the Test firewall depends on that separation, Blueprint §7.1); persona turns are LLM-backed but this change must be fully testable without network (model wiring lands in add-stage-engines); all provenance flows through the journal schema from add-journal-ledger.

## Goals / Non-Goals

**Goals:**

- Governance in code: grounding, abstention, firewall, quota, criteria-freeze are enforced by the engine, not by prompt text alone.
- Deterministic, seedable casting so panels are reproducible and firewall checks are manifest-based.
- A corpus abstraction simple enough for MVP (local files) but honest about span citation.

**Non-Goals:**

- Retrieval sophistication (embeddings/vector stores). MVP corpus is small; exact-span selection by the model over provided context is acceptable.
- Calibration reporting against real-study benchmarks (Blueprint Horizon 3).
- Real-user recruitment integration.

## Decisions

1. **Persona = data, behavior = generator seam** — `Persona` (pydantic: profile, OCEAN variance, role, grounding scope, seed) is pure data journaled in the manifest. A `PersonaTurnGenerator` protocol (`answer(persona, question, context) -> GroundedAnswer | Abstention`) is implemented later by model-ops; tests use scripted fakes. This keeps every governance rule testable now.
2. **Casting via seeded sampling over declared segment axes** — the brief declares segments; casting expands them into profiles using a seeded RNG and documented sampling tables (age/context/attitude axes + OCEAN jitter). Alternative: fully LLM-generated personas — rejected for reproducibility; the LLM may *flesh out* narrative from the sampled profile, but identity-bearing parameters come from the sampler.
3. **Corpus as content-addressed local files** — `corpus/` in the session workspace; each source ingested with an id and SHA-256; citations are `(source_id, start_line, end_line)`. Verifying a citation = re-reading the span. Alternative: page/char offsets — line spans are good enough and human-checkable.
4. **Grounding enforced post-hoc, not just prompted** — the engine validates each `GroundedAnswer`'s citations against the corpus (span exists, non-empty); a failed validation converts the answer to an abstention with reason `citation_invalid`. This is the PersonaCite pattern with a hard backstop.
5. **Firewall as manifest set-intersection** — persona identity keys (profile hash + seed) from journaled manifests; disjointness check is pure and journaled. No reliance on prompt instructions.
6. **Criteria freeze as an ordinary journal event + orchestrator refusal** — immutability is derived state (criteria event exists → mutation refused), same pattern as gates.

## Risks / Trade-offs

- [Synthetic answers too shallow for real decisions (practitioner literature)] → by design: abstention + research debt + `requires_real_validation` propagation make shallowness visible instead of hiding it; the Dossier states it.
- [Span citation over large corpora exceeds context] → MVP caps corpus size per question via scoped grounding (persona grounding scope selects sources); revisit retrieval when corpora grow.
- [Seeded sampling produces stereotyped personas] → sampling tables reviewed as code (spec'd axes), OCEAN jitter adds within-segment variance; skeptic/feasibility/viability roles guarantee non-demographic voices.

## Open Questions

- None blocking. Calibration benchmarks deferred to a later change per Blueprint Horizon 3.
