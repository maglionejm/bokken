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
from bokken.panel.corpus import Corpus
from bokken.stages.base import (
    FACILITATOR,
    FOUNDER,
    RouterFactory,
    dumps,
    open_stage,
    opportunities_text,
    structured,
)
from bokken.stages.schemas import IdeaBatch, NoveltyVerdict, SkepticChallenge, Votes

NOVELTY_WINDOW = 6  # default; override via config ideation.novelty_window
DEFAULT_CRITERIA = ["desirability", "feasibility", "viability"]


class IdeateEngine:
    def __init__(self, router_factory: RouterFactory) -> None:
        self.router_factory = router_factory

    def run(self, ctx: StageContext) -> StageOutcome | None:
        router = self.router_factory(ctx.store)
        state = ctx.state
        config = state.config.get("ideation", {})
        quota = config.get("quota", 3)
        window = config.get("novelty_window", NOVELTY_WINDOW)
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
                    "outcomes": opportunities_text(replay(ctx.store.events())),
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
            window_slice = novelty[-window:]
            rate = sum(window_slice) / len(window_slice) if window_slice else 1.0
            if ctx.kata is not None and len(novelty) >= window:
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
            code_context = self._code_context(ctx)
            lenses = [
                (
                    "feasibility",
                    "Lens: adversarial feasibility review. Below is the actual product "
                    "corpus - review each option against what the code and docs really "
                    "support. For each option set verdict green (buildable on existing "
                    "seams), amber (buildable with a named gap), or red (not honestly "
                    "buildable as scoped - a veto), plus first_slice (the first honest "
                    "slice worth shipping) and effort S/M/L.\n\nProduct corpus "
                    "excerpt:\n" + code_context,
                ),
                (
                    "viability",
                    "Lens: independent product-owner RICE scoring. You have NO access "
                    "to the codebase - judge from the option summaries and problem "
                    "alone. For each option state Reach, Impact, Confidence, and "
                    "Effort in person-weeks in your position, and fold RICE = "
                    "(Reach x Impact x Confidence) / Effort into your scores.",
                ),
                (
                    "desirability",
                    "Lens: segment desirability against the desired-outcome ranking "
                    "below - score how directly each option serves the "
                    "highest-opportunity outcomes.\n\nOutcome ranking:\n"
                    + opportunities_text(state),
                ),
            ]
            totals: dict[str, int] = {}
            positions = []
            vetoes: dict[str, str] = {}
            for lens_name, lens in lenses:
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
                        "participant": f"the {lens_name} lens",
                        "lens": lens,
                    },
                )
                if votes is None:
                    return None
                for vote in votes.votes:
                    totals[vote.option_id] = totals.get(vote.option_id, 0) + sum(
                        vote.scores.values()
                    )
                    position = vote.position
                    if lens_name == "feasibility" and vote.verdict:
                        position = (
                            f"verdict {vote.verdict}"
                            + (f", effort {vote.effort}" if vote.effort else "")
                            + (f", first slice: {vote.first_slice}" if vote.first_slice else "")
                            + f" - {position}"
                        )
                        if vote.verdict == "red":
                            vetoes[vote.option_id] = position
                    positions.append({"actor": lens_name, "position": position})
            by_id = {o.id: o for o in options}
            ranked_ids = sorted(totals, key=lambda k: totals[k], reverse=True) or [options[0].id]
            # A red feasibility verdict is a veto: prefer the best non-red option.
            winner_id = next((i for i in ranked_ids if i not in vetoes), ranked_ids[0])
            winner = by_id.get(winner_id, options[0])
            dissent = [
                {"actor": "feasibility", "reservation": f"red verdict on {oid}: {why}"}
                for oid, why in vetoes.items()
            ]

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

    @staticmethod
    def _code_context(ctx: StageContext) -> str:
        from pathlib import Path

        config = ctx.state.config.get("panel", {})
        corpus = Corpus.ingest_inputs(
            ctx.state.brief.get("inputs", {}),
            base=Path(config.get("input_base", ".")),
            roots=config.get("input_roots"),
        )
        scope = corpus.ids_of_kind("code", "document") or corpus.source_ids
        return corpus.context_for(scope) or "(no repository on file)"

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
