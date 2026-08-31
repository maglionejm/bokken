"""The DT stage state machine: legal edges and stage entry/exit criteria."""

from __future__ import annotations

from dataclasses import dataclass, field

from bokken.journal import SessionState, Stage

FORWARD: dict[Stage, Stage] = {
    "intake": "empathize",
    "empathize": "define",
    "define": "ideate",
    "ideate": "prototype",
    "prototype": "test",
    "test": "complete",
}

LOOPBACKS: frozenset[tuple[Stage, Stage]] = frozenset(
    {("test", "define"), ("test", "empathize"), ("define", "empathize")}
)

TRANSITIONS: frozenset[tuple[Stage, Stage]] = frozenset(FORWARD.items()) | LOOPBACKS


def is_legal(from_stage: Stage, to_stage: Stage) -> bool:
    return (from_stage, to_stage) in TRANSITIONS


def is_loopback(from_stage: Stage, to_stage: Stage) -> bool:
    return (from_stage, to_stage) in LOOPBACKS


def legal_targets(from_stage: Stage) -> list[Stage]:
    return sorted(to for f, to in TRANSITIONS if f == from_stage)


class IllegalTransitionError(Exception):
    def __init__(self, from_stage: Stage, to_stage: Stage) -> None:
        self.from_stage = from_stage
        self.to_stage = to_stage
        legal = ", ".join(legal_targets(from_stage)) or "none"
        super().__init__(
            f"illegal transition {from_stage} -> {to_stage}; legal targets from "
            f"{from_stage}: {legal}"
        )


@dataclass(frozen=True)
class CriteriaVerdict:
    ok: bool
    unmet: list[str] = field(default_factory=list)


def justification_refs(stage: Stage, state: SessionState) -> list[str]:
    """Event ids that justify leaving ``stage`` forward — recorded on the transition."""
    if stage == "empathize":
        return [*state.evidence, *(d.id for d in state.research_debt)]
    if stage in ("define", "ideate", "test"):
        return [d.id for d in state.decisions.values() if d.stage == stage]
    if stage == "prototype":
        return [a.id for a in state.artifacts]
    return []


def can_exit(stage: Stage, state: SessionState) -> CriteriaVerdict:
    """Evaluate the stage's forward-exit criteria against replayed state."""
    unmet: list[str] = []
    if stage == "intake":
        if not state.brief:
            unmet.append("intake: a validated brief must exist")
    elif stage == "empathize":
        segments = state.brief.get("target_segments", [])
        covered_by_evidence = {e.segment for e in state.evidence.values() if e.segment}
        covered_by_debt = {d.segment for d in state.research_debt if d.segment}
        for segment in segments:
            if segment not in covered_by_evidence and segment not in covered_by_debt:
                unmet.append(
                    f"empathize: segment '{segment}' has neither evidence nor a "
                    "research-debt abstention"
                )
        if not state.evidence and not state.research_debt:
            unmet.append("empathize: no evidence captured")
    elif stage == "define":
        if not any(d.stage == "define" for d in state.decisions.values()):
            unmet.append("define: no problem-statement decision recorded")
        if not any(i.refs and not i.ungrounded for i in state.insights.values()):
            unmet.append("define: no evidence-linked insight exists")
    elif stage == "ideate":
        if not any(o.status == "alive" for o in state.options.values()):
            unmet.append("ideate: no surviving option")
        if not any(d.stage == "ideate" for d in state.decisions.values()):
            unmet.append("ideate: no convergence decision recorded")
    elif stage == "prototype":
        if not state.assumptions:
            unmet.append("prototype: assumption register is empty")
        if not state.artifacts:
            unmet.append("prototype: no artifact generated")
    elif stage == "test":
        unscored = [a for a in state.assumptions.values() if a.score is None]
        if unscored:
            unmet.append(f"test: {len(unscored)} assumption(s) not yet scored")
        if not any(d.stage == "test" for d in state.decisions.values()):
            unmet.append("test: no kill/iterate/proceed recommendation recorded")
    elif stage == "complete":
        unmet.append("complete: terminal stage has no forward exit")
    return CriteriaVerdict(ok=not unmet, unmet=unmet)
