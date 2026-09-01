"""Empathize engine: interview program, adaptive laddering, evidence with provenance."""

from __future__ import annotations

from pathlib import Path

from bokken.journal import replay
from bokken.journal.schema import content_hash
from bokken.orchestrator import StageContext, StageOutcome
from bokken.panel import Corpus, Interviewer, cast_panel, journal_manifest
from bokken.stages.base import (
    FACILITATOR,
    FOUNDER,
    RouterFactory,
    dumps,
    evidence_lines,
    open_stage,
    structured,
)
from bokken.stages.persona_gen import RouterTurnGenerator
from bokken.stages.schemas import FollowUp, InterviewProgram, OutcomeList, OutcomeScores
from bokken.stages.walkthrough import run_walkthrough

OPPORTUNITY_BANDS = ((15.0, "severely underserved"), (12.0, "underserved"), (10.0, "moderate"))
SEGMENT_SPIKE = 17.0


def opportunity_band(score: float, bands=None) -> str:
    for floor, band in bands or OPPORTUNITY_BANDS:
        if score >= floor:
            return band
    return "served"


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
            # Mode parity: a running app deserves its functional test either way.
            run_walkthrough(ctx, router)
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
        # Observed facts about the running product feed the outcome derivation.
        run_walkthrough(ctx, router)
        self._outcome_ranking(ctx, router, segment_personas)

    def _outcome_ranking(self, ctx: StageContext, router, personas) -> None:
        """JTBD: derive desired outcomes, score I/S per persona, journal the
        deterministic Ulwick opportunity ranking (Opp = I + max(I - S, 0))."""
        state = replay(ctx.store.events())
        bands_cfg = state.config.get("empathize", {})
        if not state.evidence or any(i.kind == "opportunity" for i in state.insights.values()):
            return
        outcome_list = structured(
            router,
            "research",
            "empathize/outcomes",
            OutcomeList,
            stage="empathize",
            params={"brief": dumps(state.brief), "evidence": evidence_lines(ctx.store)},
        )
        if outcome_list is None:
            return
        known = set(state.evidence)
        outcome_events = []
        for draft in outcome_list.outcomes:
            refs = [e for e in draft.evidence_ids if e in known]
            outcome_events.append(
                ctx.store.append(
                    type="interpretation.derived",
                    stage="empathize",
                    actor=FACILITATOR,
                    payload={
                        "kind": "desired_outcome",
                        "statement": draft.statement,
                        "ungrounded": not refs,
                        "job_step": draft.job_step,
                    },
                    refs=refs,
                )
            )
        outcomes_text = "\n".join(
            f"{i}. {e.payload['statement']}" for i, e in enumerate(outcome_events)
        )
        # importance/satisfaction per persona; extreme scores must carry reasons
        matrix: dict[int, list[tuple[str, int, int]]] = {i: [] for i in range(len(outcome_events))}
        score_refs: dict[int, list[str]] = {i: [] for i in range(len(outcome_events))}
        for persona in personas:
            scores = structured(
                router,
                "research",
                "empathize/outcome_scores",
                OutcomeScores,
                stage="empathize",
                params={"persona": dumps(persona.model_dump()), "outcomes": outcomes_text},
            )
            if scores is None:
                return
            for s in scores.scores:
                if not 0 <= s.outcome_index < len(outcome_events):
                    continue
                event = ctx.store.append(
                    type="interpretation.derived",
                    stage="empathize",
                    actor=persona.actor(),
                    payload={
                        "kind": "outcome_score",
                        "statement": (
                            f"{persona.name} scores outcome {s.outcome_index}: "
                            f"importance {s.importance}, satisfaction {s.satisfaction}"
                            + (f" - {s.reason}" if s.reason else "")
                        ),
                        "ungrounded": False,
                        "importance": s.importance,
                        "satisfaction": s.satisfaction,
                        "persona_id": persona.persona_id,
                    },
                    refs=[outcome_events[s.outcome_index].id],
                )
                matrix[s.outcome_index].append((persona.name, s.importance, s.satisfaction))
                score_refs[s.outcome_index].append(event.id)

        ranked = []
        for i, outcome in enumerate(outcome_events):
            entries = matrix[i]
            if not entries:
                continue
            per_persona = {
                name: importance + max(importance - satisfaction, 0)
                for name, importance, satisfaction in entries
            }
            mean = round(sum(per_persona.values()) / len(per_persona), 1)
            band = opportunity_band(mean, bands_cfg.get("opportunity_bands"))
            spikes = sorted(
                n
                for n, v in per_persona.items()
                if v >= bands_cfg.get("segment_spike", SEGMENT_SPIKE)
            )
            ctx.store.append(
                type="interpretation.derived",
                stage="empathize",
                actor=FACILITATOR,
                payload={
                    "kind": "opportunity",
                    "statement": (
                        f"O{i}: {outcome.payload['statement']} - opportunity {mean} ({band})"
                        + (f"; segment spike: {', '.join(spikes)}" if spikes else "")
                    ),
                    "ungrounded": False,
                    "score": mean,
                    "band": band,
                    "per_persona": per_persona,
                },
                refs=[outcome.id, *score_refs[i]],
            )
            ranked.append((mean, band, i, outcome.payload["statement"], per_persona, spikes))

        ranked.sort(reverse=True)
        lines = [
            "# Opportunity ranking (Ulwick: Opp = Importance + max(Importance - Satisfaction, 0))",
            "",
            "| Rank | Outcome | Mean | Band | Per persona | Segment spike |",
            "|------|---------|------|------|-------------|---------------|",
        ]
        for rank, (mean, band, i, statement, per_persona, spikes) in enumerate(ranked, 1):
            persona_cells = ", ".join(f"{n} {v}" for n, v in sorted(per_persona.items()))
            lines.append(
                f"| {rank} | O{i} {statement} | {mean} | {band} "
                f"| {persona_cells} | {', '.join(spikes) or '-'} |"
            )
        content = "\n".join(lines) + "\n"
        path = ctx.store.session_dir / "artifacts" / "empathize" / "opportunity_ranking.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        ctx.store.append(
            type="artifact.generated",
            stage="empathize",
            actor=FACILITATOR,
            payload={
                "path": "artifacts/empathize/opportunity_ranking.md",
                "kind": "opportunity_ranking",
                "content_hash": content_hash(content),
            },
            refs=[e.id for e in outcome_events],
        )
