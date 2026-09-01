"""Prototype engine: assumption register first; artifacts chosen against the riskiest."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bokken.journal import Actor
from bokken.orchestrator import StageContext, StageOutcome
from bokken.stages.base import FACILITATOR, RouterFactory, StageError, open_stage, structured
from bokken.stages.research import prior_research, run_concept_research
from bokken.stages.schemas import AssumptionList, FidelityChoice

_RISK_ORDER = {"high": 2, "medium": 1, "low": 0}


def _exercise_wireframe(ctx: StageContext, absolute) -> None:
    """The prototype gets the same treatment as the product: a real browser pass."""
    from bokken.journal.schema import content_hash as _hash
    from bokken.stages.walkthrough import WalkerUnavailable, build_walker

    try:
        observations = build_walker().visit(absolute.as_uri(), max_pages=1)
    except (WalkerUnavailable, Exception):
        return  # honest skip: the artifact stands on its own
    for i, obs in enumerate(observations[:1], 1):
        ctx.store.append(
            type="evidence.captured",
            stage="prototype",
            actor=Actor(kind="system", name="ui-walker"),
            payload={
                "content": obs.facts(),
                "source": "wireframe_exercise",
                "confidence_class": "observed",
            },
        )
        if obs.screenshot_png:
            shot = ctx.store.session_dir / "artifacts" / "prototype" / f"wireframe_{i}.png"
            shot.write_bytes(obs.screenshot_png)
            ctx.store.append(
                type="artifact.generated",
                stage="prototype",
                actor=Actor(kind="system", name="ui-walker"),
                payload={
                    "path": f"artifacts/prototype/wireframe_{i}.png",
                    "kind": "ui_screenshot",
                    "content_hash": _hash(obs.screenshot_png),
                },
            )


def _design_tokens(ctx: StageContext) -> str:
    """Real CSS from the declared repo so wireframes speak the product's language."""
    from pathlib import Path as _P

    repo = (ctx.state.brief.get("inputs") or {}).get("repo")
    if not repo:
        return "(no repo declared - use a neutral utilitarian SaaS look)"
    chunks: list[str] = []
    budget = 12_000
    for css in sorted(_P(repo).rglob("*.css"))[:4]:
        try:
            text = css.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        take = text[: max(0, budget - sum(len(c) for c in chunks))]
        if take:
            chunks.append(f"/* {css.name} */\n{take}")
    return "\n\n".join(chunks) or "(no css found - use a neutral utilitarian SaaS look)"


class PrototypeEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        open_stage(
            ctx,
            goal="build the cheapest artifact that tests the riskiest assumption",
            method="register assumptions, choose fidelity deliberately, generate artifacts",
            exit_bar="artifacts exist, each mapped to register entries",
        )
        concept = self._concept(ctx)
        problem_statement = self._problem_statement(ctx)
        run_concept_research(ctx, router, concept=concept, problem_statement=problem_statement)

        drafts = structured(
            router,
            "cognition",
            "prototype/assumptions",
            AssumptionList,
            stage="prototype",
            params={
                "concept": concept,
                "problem_statement": problem_statement,
                "research": prior_research(ctx),
            },
        )
        if drafts is None:
            return None
        ranked = sorted(
            drafts.assumptions,
            key=lambda a: _RISK_ORDER[a.impact] + _RISK_ORDER[a.uncertainty],
            reverse=True,
        )
        registered = [
            ctx.store.append(
                type="assumption.registered",
                stage="prototype",
                actor=FACILITATOR,
                payload={
                    "statement": a.statement,
                    "impact": a.impact,
                    "uncertainty": a.uncertainty,
                },
            )
            for a in ranked
        ]

        register_text = "\n".join(
            f"{i}. [{e.payload['impact']}/{e.payload['uncertainty']}] {e.payload['statement']}"
            for i, e in enumerate(registered)
        )
        plan = structured(
            router,
            "cognition",
            "prototype/fidelity",
            FidelityChoice,
            stage="prototype",
            params={"register": register_text},
        )
        if plan is None:
            return None
        riskiest = registered[0]
        ctx.store.append(
            type="decision.recorded",
            stage="prototype",
            actor=FACILITATOR,
            payload={
                "question": "prototype fidelity: cheapest artifact testing the riskiest assumption",
                "options": [item.kind for item in plan.artifacts],
                "criteria": ["tests the riskiest assumption at the lowest cost"],
                "positions": [],
                "resolution": plan.rationale,
                "dissent": [],
            },
            refs=[riskiest.id],
        )

        for item in plan.artifacts:
            assumption_refs = [
                registered[i].id for i in item.assumption_indexes if 0 <= i < len(registered)
            ]
            if not assumption_refs:
                raise StageError(
                    f"artifact {item.kind} maps to no assumption register entry; refused"
                )
            outcome = router.invoke(
                "generation",
                "prototype/artifact",
                stage="prototype",
                params={
                    "kind": item.kind,
                    "concept": concept,
                    "design_tokens": (
                        _design_tokens(ctx) if item.kind == "wireframe_html" else "(n/a)"
                    ),
                    "problem_statement": problem_statement,
                    "assumptions": "; ".join(
                        registered[i].payload["statement"]
                        for i in item.assumption_indexes
                        if 0 <= i < len(registered)
                    ),
                },
                stream=True,
                max_tokens=64000,
            )
            if outcome.status == "budget_exhausted":
                return None
            if not outcome.ok:
                raise StageError(f"artifact generation failed: {outcome.status}")
            suffix = "html" if item.kind == "wireframe_html" else "md"
            relative = Path("artifacts") / "prototype" / f"{item.kind}.{suffix}"
            absolute = ctx.store.session_dir / relative
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text(outcome.text, encoding="utf-8")
            ctx.store.append(
                type="artifact.generated",
                stage="prototype",
                actor=FACILITATOR,
                payload={
                    "path": str(relative),
                    "kind": item.kind,
                    "content_hash": hashlib.sha256(outcome.text.encode()).hexdigest(),
                },
                refs=assumption_refs,
            )
            if item.kind == "wireframe_html":
                _exercise_wireframe(ctx, absolute)
        return None

    @staticmethod
    def _concept(ctx: StageContext) -> str:
        for decision in ctx.state.decisions.values():
            if decision.stage == "ideate":
                return decision.resolution
        raise StageError("prototype requires a convergence decision from ideate")

    @staticmethod
    def _problem_statement(ctx: StageContext) -> str:
        for decision in ctx.state.decisions.values():
            if decision.stage == "define":
                return decision.resolution
        return ctx.state.brief.get("problem_space", "")
