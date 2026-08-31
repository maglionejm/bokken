# Design: add-spec-handoff

## Context

See proposal.md. Constraints: the dossier's journal-derived `DossierModel` already carries everything the handoff needs (problem statement, concept, register with scores, recommendation, artifacts, refs); spec *content* requires generation (unlike the deterministic dossier), so it must flow through the ModelRouter; the output must strictly satisfy the OpenSpec format so `openspec validate --strict` passes in the target repo, but bokken cannot run the Node CLI itself.

## Goals / Non-Goals

**Goals:**

- One structured `cognition` call produces the whole package plan (`SpecPackage` schema); rendering to OpenSpec markdown is deterministic code.
- Format compliance guaranteed by construction: renderer normalizes (SHALL phrasing, kebab-case capabilities, scenario scaffolds) and a structural validator gates the write — never a half-written package.
- Honesty carry-over is code, not prompt: contradicted assumptions are stripped from requirements and forced into design exclusions; validation debt is forced into tasks.

**Non-Goals:**

- Running `openspec` (Node) from bokken; compliance is enforced by our validator mirroring the documented rules (covered by a target-repo validation test in CI-less form: format assertions).
- Generating implementation code or scaffolding the target repo (that is the *consumer's* job).
- Multi-change packages (one `build-mvp-<slug>` change per session in MVP).

## Decisions

1. **Reuse `dossier.build_model`** as the handoff's read model — no second journal walk, single source of derived truth.
2. **`SpecPackage` structured output** (pydantic): `{purpose, why, what_changes, capabilities: [{name, purpose, requirements: [{name, statement, scenarios: [{name, when, then}], assumption_indexes}]}], design_context, decisions, task_groups}` — the model maps register entries to requirements by index so traceability is code-derived, not model-claimed.
3. **Renderer normalization over rejection**: missing SHALL → prefix "The system SHALL"; empty scenarios → scaffold from the requirement; capability names slugified. Only unrecoverable output (zero capabilities/requirements) fails generation.
4. **Traceability in `traceability.json`, not inside spec files** — keeps the specs clean for the target repo while every requirement maps to ledger ids (concept decision, problem-statement decision, assumption events).
5. **Finalization lives in `bokken.handoff.finalize`** and is called by the surfaces (CLI `run`, MCP `run_session`) — the orchestrator stays output-agnostic. Idempotence via journal artifact kinds (`dossier_markdown`, `handoff_package`).
6. **Package root marker** — one `artifact.generated` with kind `handoff_package` on the change directory (plus one per file) makes idempotence and status checks a journal query.

## Risks / Trade-offs

- [Generated requirements may drift from what was actually validated] → requirements must cite register indexes; anything citing a contradicted assumption is dropped by code; traceability.json exposes the mapping for review.
- [OpenSpec format changes upstream] → validator centralizes the rules in one module; a format bump is one change.
- [Finalization doubles model spend at completion] → handoff is one structured call; skipped when the package exists; `kill` short-circuits.

## Open Questions

- None blocking.
