"""Empathize engine: interview program, adaptive laddering, evidence with provenance."""

from __future__ import annotations

from pathlib import Path

from bokken.orchestrator import StageContext, StageOutcome
from bokken.panel import Corpus, Interviewer, cast_panel, journal_manifest
from bokken.stages.base import FOUNDER, RouterFactory, dumps, open_stage, structured
from bokken.stages.persona_gen import RouterTurnGenerator
from bokken.stages.schemas import FollowUp, InterviewProgram


def _describe_inputs(inputs: dict) -> str:
    parts = []
    if inputs.get("repo"):
        parts.append("an application repository (source code and configuration)")
    if inputs.get("metrics"):
        parts.append(f"{len(inputs['metrics'])} business/performance metrics file(s)")
    if inputs.get("discussions"):
        parts.append(f"{len(inputs['discussions'])} interview/discussion transcript(s)")
    if inputs.get("documents"):
        parts.append(f"{len(inputs['documents'])} document(s)")
    return "; ".join(parts) or "no tangible inputs - only the brief itself"


class EmpathizeEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        open_stage(
            ctx,
            goal="understand the people in the problem space",
            method="structured interviews with laddering follow-ups",
            exit_bar="every target segment has evidence or an explicit research-debt gap",
        )
        program = structured(
            router,
            "research",
            "empathize/interview_program",
            InterviewProgram,
            stage="empathize",
            params={
                "brief": dumps(ctx.state.brief),
                "inputs_available": _describe_inputs(ctx.state.brief.get("inputs", {})),
            },
        )
        if program is None:
            return None
        if ctx.state.mode == "dojo":
            self._dojo_interviews(ctx, router, program)
        else:
            self._founder_interviews(ctx, router, program)
        return None

    def _founder_interviews(self, ctx: StageContext, router, program: InterviewProgram) -> None:
        for q in program.questions:
            answer = ctx.input_port.ask(q.question)
            if not answer.strip() or answer.strip().lower() == "skip":
                ctx.store.append(
                    type="evidence.abstained",
                    stage="empathize",
                    actor=FOUNDER,
                    payload={
                        "question": q.question,
                        "gap": "the founder could not answer; needs real research",
                        "segment": q.segment,
                    },
                )
                continue
            ctx.store.append(
                type="evidence.captured",
                stage="empathize",
                actor=FOUNDER,
                payload={
                    "content": answer,
                    "source": "founder interview",
                    "confidence_class": "reported",
                    "segment": q.segment,
                },
            )
            followup = structured(
                router,
                "research",
                "empathize/followup",
                FollowUp,
                stage="empathize",
                params={"question": q.question, "answer": answer},
            )
            if followup and followup.question:
                follow_answer = ctx.input_port.ask(followup.question)
                if follow_answer.strip():
                    ctx.store.append(
                        type="evidence.captured",
                        stage="empathize",
                        actor=FOUNDER,
                        payload={
                            "content": follow_answer,
                            "source": "founder interview (laddering)",
                            "confidence_class": "reported",
                            "segment": q.segment,
                        },
                    )

    def _dojo_interviews(self, ctx: StageContext, router, program: InterviewProgram) -> None:
        config = ctx.state.config.get("panel", {})
        corpus = Corpus.ingest_inputs(
            ctx.state.brief.get("inputs", {}), base=Path(config.get("input_base", "."))
        )
        personas = cast_panel(
            brief=ctx.state.brief,
            size=config.get("size", 6),
            seed=config.get("seed", 7),
            grounding_sources=corpus.source_ids,
        )
        # Feasibility and viability voices ground on the product and the numbers.
        scoped = []
        for persona in personas:
            if persona.role == "feasibility":
                scope = corpus.ids_of_kind("code", "metrics") or corpus.source_ids
                persona = persona.model_copy(update={"grounding_scope": scope})
            elif persona.role == "viability":
                scope = corpus.ids_of_kind("metrics") or corpus.source_ids
                persona = persona.model_copy(update={"grounding_scope": scope})
            scoped.append(persona)
        journal_manifest(
            ctx.store,
            personas=scoped,
            panel_kind="interview",
            seed=config.get("seed", 7),
            stage="empathize",
        )
        interviewer = Interviewer(corpus, RouterTurnGenerator(router), ctx.store)
        segment_personas = [p for p in scoped if p.role == "segment"]
        for q in program.questions:
            targets = [p for p in segment_personas if p.segment == q.segment] or segment_personas
            for persona in targets:
                interviewer.ask(persona, q.question, stage="empathize", segment=q.segment)
