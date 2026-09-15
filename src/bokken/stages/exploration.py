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

# A citation's journaled quote is a readability aid, not the evidence itself
# (the span stays resolvable from the corpus): cap it so one generous span
# cannot balloon the journal record.
QUOTE_CAP_CHARS = 200


def quoted_citations(corpus, citations) -> list[dict]:
    """Citation dicts with a truncated verbatim `quote` of each resolved span.

    Deterministic and model-free: the quote is the corpus text the citation
    already validated against, capped at QUOTE_CAP_CHARS. The label stays
    "cited", never "proven" - a readable quote proves nothing extra.
    """
    quoted = []
    for citation in citations:
        span = corpus.span(citation) or ""
        if len(span) > QUOTE_CAP_CHARS:
            span = span[: QUOTE_CAP_CHARS - 3].rstrip() + "..."
        quoted.append({**citation.model_dump(), "quote": span})
    return quoted


def _ask_ratification(input_port, statement: str):
    """One compact founder prompt per capability: confirm / dispute / skip.

    Returns (verdict, correction, answer): verdict is "confirm", "dispute" or
    "skip"; on a dispute the correction is non-empty and `answer` carries the
    provenance of whoever supplied it. A bare "d" gets one follow-up ask for
    the correction; a dispute nobody corrects degrades to a skip. Anything
    unrecognized is a skip - ratification never invents a verdict.
    """
    answer = input_port.ask(
        f"Code exploration mapped: {statement}\nConfirm, dispute, or skip? [c/d/s]"
    )
    token, _, rest = answer.text.strip().partition(" ")
    token = token.rstrip(":,.").lower()
    if token in ("c", "confirm"):
        return "confirm", "", answer
    if token in ("d", "dispute"):
        correction = rest.strip().lstrip(":,-").strip()
        if not correction:
            answer = input_port.ask("What does the product actually do instead?")
            correction = answer.text.strip()
        if correction:
            return "dispute", correction, answer
    return "skip", "", answer


def run_code_exploration(corpus, store, router, input_port=None) -> str | None:
    """Journal current_capability interpretations from the code corpus.

    Returns a compact text rendering for downstream prompts ("" when the
    session has no code sources), or None when the call's budget is exhausted -
    the caller must return early so the orchestrator stops the run. Citations
    are validated against the corpus and must point at code sources; a
    capability whose citations all fail is journaled as ungrounded.

    With an ``input_port`` (founder mode), each capability is put to the
    founder before it is journaled: a confirmation marks the interpretation
    ``ratified: true``, a dispute marks it ``ratified: false`` and journals
    the correction as evidence ref'ing it, a skip adds nothing. `InputRequired`
    propagates like every other founder ask.
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
        payload = {
            "kind": "current_capability",
            "statement": statement,
            "ungrounded": not valid,
            "citations": quoted_citations(corpus, valid),
        }
        verdict, correction, answer = (
            _ask_ratification(input_port, statement) if input_port else ("skip", "", None)
        )
        if verdict == "confirm":
            payload["ratified"] = True
        elif verdict == "dispute":
            payload["ratified"] = False
        event = store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=result.actor("code-explorer"),
            payload=payload,
        )
        if verdict == "dispute":
            store.append(
                type="evidence.captured",
                stage="empathize",
                actor=answer.actor,
                payload={
                    "content": correction,
                    "source": answer.source("founder ratification of the capability map"),
                    "confidence_class": answer.confidence_class("reported"),
                },
                refs=[event.id],
            )
        lines.append(f"- {statement}" + ("" if valid else " (ungrounded)"))
    for term in result.data.glossary:
        # The glossary plays by the capability rules: only a resolvable span in
        # a code source grounds a term, and every kept citation carries a quote.
        valid = [
            c
            for c in term.citations
            if corpus.kind_of(c.source_id) == "code" and corpus.validate_citation(c)
        ]
        store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=result.actor("code-explorer"),
            payload={
                "kind": "domain_term",
                "statement": f"{term.term}: {term.meaning}",
                "ungrounded": not valid,
                "citations": quoted_citations(corpus, valid),
            },
        )
    return "\n".join(lines)
