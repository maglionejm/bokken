"""Code exploration: a cited map of what the product does today.

Adapted from the exploration discipline in `build-software-with-style`
(enterprise template): sources carry declared evidence roles, and current
behavior is registered as typed, cited findings before anyone is interviewed
- so desired outcomes are framed against implemented reality, not guesses.
"""

from __future__ import annotations

from bokken.stages.base import structured
from bokken.stages.schemas import CapabilityMap

# The capability map is a single uncached call per session (no loop ever reads
# its prefix back), so the whole corpus rides as fresh input at full price: cap
# it well below the 4MB corpus ingest budget. 120k chars (~30k tokens) matches
# the persona-turn delegation threshold and fits every routed model.
CODE_CONTEXT_CAP_CHARS = 120_000


def run_code_exploration(corpus, store, router) -> str | None:
    """Journal current_capability interpretations from the code corpus.

    Returns a compact text rendering for downstream prompts ("" when the
    session has no code sources), or None when the call's budget is exhausted -
    the caller must return early so the orchestrator stops the run. Citations
    are validated against the corpus and must point at code sources; a
    capability whose citations all fail is journaled as ungrounded.
    """
    code_ids = corpus.ids_of_kind("code")
    if not code_ids:
        return ""
    result = structured(
        router,
        "cognition",
        "explore/capability_map",
        CapabilityMap,
        stage="empathize",
        params={"context": corpus.context_for(code_ids)[:CODE_CONTEXT_CAP_CHARS]},
    )
    if result is None:
        return None
    lines: list[str] = []
    for cap in result.data.capabilities:
        # Only code establishes implemented behavior: a resolvable span in a
        # metrics or discussion source still does not ground a capability.
        valid = [
            c
            for c in cap.citations
            if corpus.kind_of(c.source_id) == "code" and corpus.validate_citation(c)
        ]
        statement = f"{cap.name}: {cap.actor} {cap.trigger} -> {cap.outcome}"
        store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=result.actor("code-explorer"),
            payload={
                "kind": "current_capability",
                "statement": statement,
                "ungrounded": not valid,
                "citations": [c.model_dump() for c in valid],
            },
        )
        lines.append(f"- {statement}" + ("" if valid else " (ungrounded)"))
    return "\n".join(lines)
