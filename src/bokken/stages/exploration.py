"""Code exploration: a cited map of what the product does today.

Adapted from the exploration discipline in `build-software-with-style`
(enterprise template): sources carry declared evidence roles, and current
behavior is registered as typed, cited findings before anyone is interviewed
- so desired outcomes are framed against implemented reality, not guesses.
"""

from __future__ import annotations

from bokken.stages.base import structured
from bokken.stages.schemas import CapabilityMap


def run_code_exploration(corpus, store, router) -> str:
    """Journal current_capability interpretations from the code corpus.

    Returns a compact text rendering for downstream prompts ("" when the
    session has no code sources). Citations are validated against the corpus;
    a capability whose citations all fail is journaled as ungrounded.
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
        params={"context": corpus.context_for(code_ids)},
    )
    if result is None:
        return ""
    lines: list[str] = []
    for cap in result.data.capabilities:
        valid = [c for c in cap.citations if corpus.validate_citation(c)]
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
