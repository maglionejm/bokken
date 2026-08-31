"""Ideate engine: governed divergence with novelty monitoring, then convergence."""

from __future__ import annotations

from bokken.journal import Event, replay
from bokken.orchestrator import StageContext, StageOutcome
from bokken.panel import (
    cast_panel,
    freeze_criteria,
    frozen_criteria,
    journal_manifest,
    require_skeptic_challenge,
)
from bokken.stages.base import FACILITATOR, FOUNDER, RouterFactory, dumps, open_stage, structured
from bokken.stages.schemas import IdeaBatch, NoveltyVerdict, SkepticChallenge, Votes

NOVELTY_WINDOW = 6
DEFAULT_CRITERIA = ["desirability", "feasibility", "viability"]


class IdeateEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        state = ctx.state
        config = state.config.get("ideation", {})
        quota = config.get("quota", 3)
        floor = config.get("novelty_floor") or state.config.get("budgets", {}).get(
            "novelty_floor", 0.2
        )
        open_stage(
            ctx,
            goal="generate genuinely different options, then converge deliberately",
            method="quota-driven divergence with novelty monitoring; criteria-scored convergence",
            exit_bar="a surviving option selected under the frozen criteria",
        )
        if frozen_criteria(state) is None:
            freeze_criteria(ctx.store, criteria=config.get("criteria", DEFAULT_CRITERIA))

        problem_statement = self._problem_statement(state)
        if state.mode == "dojo":
            personas = self._dojo_panel(ctx)
            participants = [(p.name, p.actor(), p) for p in personas if p.role == "segment"]
            skeptic = next(p for p in personas if p.role == "skeptic")
        else:
            participants = [("facilitator", FACILITATOR, None)]
            skeptic = None

        options: list[Event] = []
        clusters: list[str] = []
        novelty: list[bool] = []
        pivoted = False
        for name, actor, persona in participants:
            batch = structured(
                router,
                "cognition",
                "ideate/diverge",
                IdeaBatch,
                stage="ideate",
                params={
                    "problem_statement": problem_statement,
                    "participant": name,
                    "existing": "; ".join(clusters) or "(none)",
                    "quota": quota,
                },
            )
            if batch is None:
                return None
            for idea in batch.ideas[:quota]:
                payload = {"summary": idea.summary}
                if persona is not None and idea.private_thought:
                    payload["private_thought"] = idea.private_thought
                    payload["visibility"] = "private_thought_attached"
                option = ctx.store.append(
                    type="option.created", stage="ideate", actor=actor, payload=payload
                )
                options.append(option)
                verdict = structured(
                    router,
                    "extraction",
                    "ideate/novelty",
                    NoveltyVerdict,
                    stage="ideate",
                    params={"clusters": "\n".join(clusters) or "(none)", "option": idea.summary},
                )
                is_novel = verdict is not None and verdict.classification == "novel_cluster"
                if is_novel:
                    clusters.append(idea.summary)
                novelty.append(is_novel)
            window = novelty[-NOVELTY_WINDOW:]
            rate = sum(window) / len(window) if window else 1.0
            if ctx.kata is not None and len(novelty) >= NOVELTY_WINDOW:
                event = ctx.kata.evaluate(
                    "timebox_pivot",
                    replay(ctx.store.events()),
                    {"novelty_rate": rate, "novelty_floor": floor},
                    stage="ideate",
                    mode=state.mode or "founder",
                )
                if event is not None and event.type == "facilitation.move_executed":
                    pivoted = True
                    break

        if state.mode == "founder":
            self._founder_contributions(ctx, options)

        # Convergence: the skeptic must be on record first (Dojo panels).
        if skeptic is not None:
            challenge = structured(
                router,
                "challenge",
                "ideate/skeptic_challenge",
                SkepticChallenge,
                stage="ideate",
                params={"options": self._options_text(options)},
            )
            if challenge is None:
                return None
            ctx.store.append(
                type="evidence.captured",
                stage="ideate",
                actor=skeptic.actor(),
                payload={
                    "content": challenge.challenge,
                    "source": f"persona:{skeptic.persona_id}",
                    "confidence_class": "simulated",
                    "speaker": skeptic.name,
                    "grounding": "profile",
                },
            )
            require_skeptic_challenge(replay(ctx.store.events()), {skeptic.persona_id})

        return self._converge(ctx, router, options, problem_statement, pivoted)

    def _converge(
        self,
        ctx: StageContext,
        router,
        options: list[Event],
        problem_statement: str,
        pivoted: bool,
    ) -> StageOutcome | None:
        state = replay(ctx.store.events())
        criteria = frozen_criteria(state) or DEFAULT_CRITERIA
        if state.mode == "founder":
            choice = ctx.input_port.ask(
                "Pick the option to advance (number):\n" + self._options_text(options)
            )
            try:
                winner = options[int(choice.strip()) - 1]
            except (ValueError, IndexError):
                winner = options[0]
            positions = [{"actor": "founder", "position": winner.payload["summary"]}]
            dissent: list[dict[str, str]] = []
        else:
            votes = structured(
                router,
                "challenge",
                "ideate/converge",
                Votes,
                stage="ideate",
                params={
                    "problem_statement": problem_statement,
                    "criteria": ", ".join(criteria),
                    "options": self._options_text(options),
                    "participant": "the panel (skeptic, feasibility, viability, segments)",
                },
            )
            if votes is None:
                return None
            totals: dict[str, int] = {}
            positions = []
            for vote in votes.votes:
                totals[vote.option_id] = totals.get(vote.option_id, 0) + sum(vote.scores.values())
                positions.append({"actor": vote.option_id, "position": vote.position})
            by_id = {o.id: o for o in options}
            winner_id = max(totals, key=lambda k: totals[k]) if totals else options[0].id
            winner = by_id.get(winner_id, options[0])
            dissent = [
                {"actor": "skeptic", "reservation": p["position"]}
                for p in positions
                if "concern" in p["position"].lower() or "risk" in p["position"].lower()
            ][:1]

        for option in options:
            if option.id != winner.id:
                ctx.store.append(
                    type="option.killed",
                    stage="ideate",
                    actor=FACILITATOR,
                    payload={"reason": "outscored under the frozen criteria"},
                    refs=[option.id],
                )
        ctx.store.append(
            type="decision.recorded",
            stage="ideate",
            actor=FACILITATOR if state.mode == "dojo" else FOUNDER,
            payload={
                "question": "which concept advances to prototype",
                "options": [o.id for o in options],
                "criteria": criteria,
                "positions": positions,
                "resolution": winner.payload["summary"],
                "dissent": dissent,
                "requires_real_validation": state.mode == "dojo",
                "pivoted_by_timebox": pivoted,
            },
            refs=[winner.id],
        )
        return None

    def _founder_contributions(self, ctx: StageContext, options: list[Event]) -> None:
        while True:
            idea = ctx.input_port.ask("Add your own option (empty to finish):")
            if not idea.strip():
                break
            options.append(
                ctx.store.append(
                    type="option.created",
                    stage="ideate",
                    actor=FOUNDER,
                    payload={"summary": idea.strip()},
                )
            )

    def _dojo_panel(self, ctx: StageContext):
        config = ctx.state.config.get("panel", {})
        seed = config.get("seed", 7) + 500  # distinct from the interview panel
        personas = cast_panel(brief=ctx.state.brief, size=config.get("size", 6), seed=seed)
        journal_manifest(
            ctx.store, personas=personas, panel_kind="ideation", seed=seed, stage="ideate"
        )
        return personas

    @staticmethod
    def _options_text(options: list[Event]) -> str:
        return "\n".join(f"{i + 1}. {o.id}: {o.payload['summary']}" for i, o in enumerate(options))

    @staticmethod
    def _problem_statement(state) -> str:
        for decision in state.decisions.values():
            if decision.stage == "define":
                return decision.resolution
        return dumps(state.brief.get("problem_space", ""))
