"""Test engine: firewalled evaluation, scored register, kill/iterate/proceed."""

from __future__ import annotations

from bokken.journal import replay
from bokken.orchestrator import StageContext, StageOutcome
from bokken.panel import cast_panel, check_firewall, journal_manifest
from bokken.stages.base import FOUNDER, RouterFactory, dumps, facilitator, open_stage, structured
from bokken.stages.schemas import Evaluation, Recommendation

_SCORES = ("supported", "contradicted", "untested")


class TestEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        open_stage(
            ctx,
            goal="score the assumption register against honest reactions",
            method="fresh-panel evaluation (Dojo) or structured read-through (Founder)",
            exit_bar="every assumption scored and a kill/iterate/proceed recommendation recorded",
        )
        artifact_text, artifact_kind = self._primary_artifact(ctx)
        assumptions = list(ctx.state.assumptions.values())

        if ctx.state.mode == "dojo":
            if not self._dojo_evaluate(ctx, router, artifact_text, artifact_kind, assumptions):
                return None
        else:
            self._founder_evaluate(ctx, assumptions)

        return self._recommend(ctx, router)

    def _dojo_evaluate(self, ctx, router, artifact_text, artifact_kind, assumptions) -> bool:
        config = ctx.state.config.get("panel", {})
        seed = config.get("seed", 7) + 9000  # never the panel that ideated
        panel = cast_panel(brief=ctx.state.brief, size=config.get("size", 6), seed=seed)
        journal_manifest(ctx.store, personas=panel, panel_kind="test", seed=seed, stage="test")
        check_firewall(ctx.store, panel)
        reviewers = [p for p in panel if p.role == "segment"] or panel
        for i, assumption in enumerate(assumptions):
            persona = reviewers[i % len(reviewers)]
            evaluation = structured(
                router,
                "challenge",
                "test/evaluate",
                Evaluation,
                stage="test",
                params={
                    "persona": dumps(persona.model_dump()),
                    "kind": artifact_kind,
                    "artifact": artifact_text,
                    "assumption": assumption.statement,
                },
            )
            if evaluation is None:
                return False
            reaction = ctx.store.append(
                type="evidence.captured",
                stage="test",
                actor=persona.actor(router.routing["challenge"]),
                payload={
                    "content": evaluation.reaction,
                    "source": f"persona:{persona.persona_id}",
                    "confidence_class": "simulated",
                    "speaker": persona.name,
                    "grounding": "evaluation",
                },
            )
            ctx.store.append(
                type="assumption.scored",
                stage="test",
                actor=persona.actor(router.routing["challenge"]),
                payload={"score": evaluation.score, "rationale": evaluation.reaction},
                refs=[assumption.id, reaction.id],
            )
        return True

    def _founder_evaluate(self, ctx, assumptions) -> None:
        for assumption in assumptions:
            raw = ctx.input_port.ask(
                f"Assumption: {assumption.statement}\n"
                "After the read-through, is it supported, contradicted, or untested? "
                "Answer '<score>: <why>'."
            )
            score, _, why = raw.partition(":")
            score = score.strip().lower()
            if score not in _SCORES:
                score = "untested"
            reaction = ctx.store.append(
                type="evidence.captured",
                stage="test",
                actor=FOUNDER,
                payload={
                    "content": why.strip() or raw,
                    "source": "founder read-through",
                    "confidence_class": "observed",
                },
            )
            ctx.store.append(
                type="assumption.scored",
                stage="test",
                actor=FOUNDER,
                payload={"score": score, "rationale": why.strip() or None},
                refs=[assumption.id, reaction.id],
            )

    def _recommend(self, ctx, router) -> StageOutcome | None:
        state = replay(ctx.store.events())
        register_text = "\n".join(
            f"- [{a.score or 'untested'}] {a.statement}" for a in state.assumptions.values()
        )
        recommendation = structured(
            router,
            "challenge",
            "test/recommend",
            Recommendation,
            stage="test",
            params={"register": register_text},
        )
        if recommendation is None:
            return None
        contradicted = [a for a in state.assumptions.values() if a.score == "contradicted"]
        simulated_used = any(
            e.confidence_class == "simulated" and e.stage == "test" for e in state.evidence.values()
        )
        ctx.store.append(
            type="decision.recorded",
            stage="test",
            actor=facilitator(router),
            payload={
                "question": "kill, iterate, or proceed",
                "options": ["kill", "iterate", "proceed"],
                "criteria": ["assumption register scores"],
                "positions": [],
                "resolution": recommendation.recommendation,
                "dissent": [],
                "confidence": recommendation.confidence,
                "requires_real_validation": simulated_used,
            },
            refs=[a.id for a in state.assumptions.values()],
        )
        if contradicted and ctx.kata is not None:
            ctx.kata.evaluate(
                "loopback_proposal",
                state,
                {
                    "contradiction": recommendation.contradicts
                    or f"{len(contradicted)} assumption(s) contradicted in test",
                    "target_stage": "define",
                    "refs": [a.id for a in contradicted],
                },
                stage="test",
                mode=state.mode or "founder",
            )
        return None

    _PROTOTYPE_KINDS = (
        "concept_one_pager",
        "landing_copy",
        "storyboard",
        "demo_script",
        "wireframe_html",
    )

    @classmethod
    def _primary_artifact(cls, ctx) -> tuple[str, str]:
        candidates = [a for a in ctx.state.artifacts if a.kind in cls._PROTOTYPE_KINDS]
        if not candidates:
            return "(no artifact on file)", "none"
        artifact = candidates[0]
        path = ctx.store.session_dir / artifact.path
        text = path.read_text(encoding="utf-8") if path.exists() else "(artifact file missing)"
        return text, artifact.kind
