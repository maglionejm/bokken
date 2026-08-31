# Design: add-dossier-generator

## Context

See proposal.md. Constraints: journal-only input (determinism requirement rules out LLM narration for MVP), the JSON export is a public contract, and honesty rules are invariants — not templates that can be edited away.

## Goals / Non-Goals

**Goals:**

- Deterministic generation: same journal → same dossier (modulo timestamp).
- Part C as the canonical graph; Parts A/B rendered *from* the same intermediate model so md/json never diverge.
- Honesty rules enforced structurally (renderers receive labels; they cannot drop them).

**Non-Goals:**

- LLM-polished narrative prose (Part B is template-rendered from the graph; an optional LLM "narrative polish" pass is a future change — it would break determinism and needs its own honesty treatment).
- Interactive HTML export and push-to-tools (Confluence/Notion/Jira) — later horizon per Blueprint §5.2.
- PDF export.

## Decisions

1. **Two-phase pipeline: `journal → DossierModel → renderers`** — a typed intermediate (pydantic) holding the full graph plus derived summaries; `MarkdownRenderer` and `JsonRenderer` consume it. Guarantees md/json consistency and testability at the model level.
2. **Part B via deterministic templates over the graph** — pivotal moments are rule-derived (loop-backs, killed frontrunners, dissent on adopted decisions, gate rejections, provocations that spawned surviving options). Alternative: LLM narration — rejected for MVP (non-determinism + would require model calls the spec forbids).
3. **Labels carried in the model, not the templates** — every `DossierModel` node carries `confidence_class`/`synthetic`/`requires_real_validation`; renderers *must* print a label block for any node that has one (renderer API takes labeled nodes only). Removing a label is a type error, not a template edit.
4. **`dossier_schema_version` starts at `"1"`, additive evolution** — consumers tolerate unknown fields (mirrors the journal's tolerant-reader rule).
5. **Partial dossiers** — the model records the max stage reached; renderers gate sections on it and stamp `status: partial`.

## Risks / Trade-offs

- [Template narrative reads dry vs. Blueprint's "readable story"] → acceptable for MVP; the pivotal-moment rules give structure, and the LLM polish pass is an isolated future change.
- [Part C size on long Dojo runs] → private persona thoughts included only as flagged references, artifact contents stay on disk; JSON is a graph of references, not blobs.
- [Public-contract pressure on dossier.json] → version field + additive-only policy documented in the spec; breaking changes require a new major version and a spec delta.

## Open Questions

- None blocking.
