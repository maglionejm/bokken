"""Interview guide: deterministic derivation from research debt + untested assumptions."""

from __future__ import annotations

from dataclasses import dataclass, field

from bokken.journal import Actor, replay
from bokken.journal.schema import content_hash

GUIDE_ACTOR = Actor(kind="system", name="validation")


@dataclass(frozen=True)
class Guide:
    debt_questions: list[str] = field(default_factory=list)
    probes: list[tuple[str, str]] = field(default_factory=list)  # (assumption_id, probe)

    @property
    def empty(self) -> bool:
        return not self.debt_questions and not self.probes

    def markdown(self) -> str:
        lines = ["# Validation interview guide", ""]
        if self.debt_questions:
            lines += ["## Open research debt (ask verbatim, ladder into incidents)", ""]
            lines += [f"- {q}" for q in self.debt_questions] + [""]
        if self.probes:
            lines += ["## Assumption probes (one falsifiable question each)", ""]
            lines += [f"- ({aid[:8]}) {probe}" for aid, probe in self.probes] + [""]
        return "\n".join(lines)


def build_guide(store) -> Guide:
    state = replay(store.events())
    seen: set[str] = set()
    debt = []
    for item in state.research_debt:
        if item.question not in seen:
            seen.add(item.question)
            debt.append(item.question)
    probes = [
        (
            aid,
            f"Thinking about your own situation: {a.statement} — has that actually "
            "happened to you? Tell me about the last time.",
        )
        for aid, a in state.assumptions.items()
        if (a.score or "untested") == "untested"
    ]
    return Guide(debt_questions=debt, probes=probes)


def journal_guide(store, guide: Guide) -> str:
    """Write + journal the guide artifact; returns its relative path."""
    content = guide.markdown()
    relative = "artifacts/validation/validation_guide.md"
    path = store.session_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    store.append(
        type="artifact.generated",
        stage=None,
        actor=GUIDE_ACTOR,
        payload={
            "path": relative,
            "kind": "validation_guide",
            "content_hash": content_hash(content),
        },
    )
    return relative
