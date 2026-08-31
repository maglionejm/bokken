"""Define engine: cluster evidence into insights, frame candidates, select via IBIS."""

from __future__ import annotations

from bokken.journal import replay
from bokken.orchestrator import StageContext, StageOutcome
from bokken.panel import requires_real_validation
from bokken.stages.base import (
    FACILITATOR,
    RouterFactory,
    evidence_lines,
    open_stage,
    structured,
)
from bokken.stages.schemas import Candidates, ClusterResult, Selection


class DefineEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        open_stage(
            ctx,
            goal="frame the problem worth solving",
            method="cluster evidence into insights, reframe, select one problem statement",
            exit_bar="an evidence-linked problem statement is selected with rationale",
        )
        clusters = structured(
            router,
            "cognition",
            "define/cluster",
            ClusterResult,
            stage="define",
            params={
                "problem_space": ctx.state.brief.get("problem_space", ""),
                "evidence": evidence_lines(ctx.store),
            },
        )
        if clusters is None:
            return None
        known_evidence = set(ctx.state.evidence)
        insight_events = []
        for draft in clusters.insights:
            refs = [e for e in draft.evidence_ids if e in known_evidence]
            insight_events.append(
                ctx.store.append(
                    type="interpretation.derived",
                    stage="define",
                    actor=FACILITATOR,
                    payload={
                        "kind": "insight",
                        "statement": draft.statement,
                        "ungrounded": not refs,
                    },
                    refs=refs,
                )
            )

        insights_text = "\n".join(f"- {e.id}: {e.payload['statement']}" for e in insight_events)
        candidates = structured(
            router,
            "cognition",
            "define/candidates",
            Candidates,
            stage="define",
            params={"insights": insights_text},
        )
        if candidates is None:
            return None
        insight_ids = {e.id for e in insight_events}
        statements: list[tuple[str, list[str]]] = []
        for candidate in candidates.candidates:
            statement = candidate.statement
            if candidate.solution_shaped and ctx.kata is not None:
                ctx.kata.evaluate(
                    "hmw_reframe",
                    ctx.state,
                    {
                        "solution_shaped_statement": candidate.statement,
                        "reframe": candidate.reframe or "reach the underlying need",
                    },
                    stage="define",
                    mode=ctx.state.mode or "founder",
                )
                if candidate.reframe:
                    statement = f"How might we {candidate.reframe.rstrip('?')}?"
            statements.append((statement, [i for i in candidate.insight_ids if i in insight_ids]))

        selection = structured(
            router,
            "cognition",
            "define/select",
            Selection,
            stage="define",
            params={"candidates": "\n".join(f"{i}. {s}" for i, (s, _) in enumerate(statements))},
        )
        if selection is None:
            return None
        winner_index = min(max(selection.winner_index, 0), len(statements) - 1)
        winner_statement, winner_refs = statements[winner_index]
        why_lost = {note.index: note.why_lost for note in selection.losers}
        options = [
            s if i == winner_index else f"{s} [lost: {why_lost.get(i, 'outscored on coverage')}]"
            for i, (s, _) in enumerate(statements)
        ]
        fresh = replay(ctx.store.events())
        ctx.store.append(
            type="decision.recorded",
            stage="define",
            actor=FACILITATOR,
            payload={
                "question": "which problem statement do we take forward",
                "options": options,
                "criteria": ["evidence coverage", "clarity", "not solution-shaped"],
                "positions": [{"actor": "facilitator", "position": winner_statement}],
                "resolution": winner_statement,
                "dissent": [],
                "requires_real_validation": requires_real_validation(fresh, winner_refs),
            },
            refs=winner_refs,
        )
        return None
