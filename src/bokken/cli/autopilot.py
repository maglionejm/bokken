"""Draft a run brief from a repository: the zero-input path into a first run.

Two model calls (extraction facts, cognition draft) behind the ModelRouter
seam, journaled into a scratch store that is discarded after the cost is
read - no session exists yet, so nothing durable should either.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bokken.journal.store import JournalStore
from bokken.panel.corpus import Corpus
from bokken.report.context import call_cost_usd
from bokken.stages.base import structured
from bokken.stages.schemas import BriefDraft, ProductFacts

CONTEXT_CAP_CHARS = 60_000  # extraction-lane read; the draft never needs more


class BriefDraftError(RuntimeError):
    pass


def draft_brief_from_repo(repo: Path, metrics: list[Path], router_factory) -> tuple[dict, float]:
    """Returns (brief_dict, drafting_cost_usd). Raises BriefDraftError when the
    corpus is empty or a drafting call refuses."""
    inputs: dict = {"repo": str(repo.resolve())}
    if metrics:
        inputs["metrics"] = [str(m.resolve()) for m in metrics]
    corpus = Corpus.ingest_inputs(inputs)
    context = corpus.context_for()[:CONTEXT_CAP_CHARS]
    if not context.strip():
        raise BriefDraftError(
            f"nothing ingestible under {repo} (text/code suffixes only; see docs/operating.md)"
        )
    with tempfile.TemporaryDirectory(prefix="bokken-draft-") as scratch:
        store = JournalStore.open(Path(scratch))
        try:
            router = router_factory(store)
            facts = structured(
                router,
                "extraction",
                "intake/product_facts",
                ProductFacts,
                stage="intake",
                params={"context": context},
            )
            if facts is None:
                raise BriefDraftError("drafting stopped: extraction budget exhausted")
            draft = structured(
                router,
                "cognition",
                "intake/draft_brief",
                BriefDraft,
                stage="intake",
                params={
                    "facts": facts.data.model_dump_json(indent=2),
                    "context": context[:20_000],
                },
            )
            if draft is None:
                raise BriefDraftError("drafting stopped: cognition budget exhausted")
            cost = sum(
                call_cost_usd(e.payload.get("model", ""), e.payload.get("usage", {}))
                for e in store.events()
                if e.type == "model.called"
            )
        finally:
            store.close()
    d = draft.data
    return (
        {
            "problem_space": d.problem_space,
            "target_segments": d.target_segments,
            "success_criteria": d.success_criteria,
            "constraints": d.constraints,
            "risk_tolerance": "medium",
            "inputs": inputs,
        },
        round(cost, 2),
    )
