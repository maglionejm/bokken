"""Router-backed persona turn generation for Dojo interviews and evaluations."""

from __future__ import annotations

from bokken.models.router import ModelRouter
from bokken.panel import Abstention, GroundedAnswer, Persona, ProfileOpinion
from bokken.stages.base import dumps
from bokken.stages.schemas import PersonaTurn

DELEGATE_THRESHOLD_CHARS = 20_000  # below this, slicing costs more than it saves


class RouterTurnGenerator:
    """Implements the panel's PersonaTurnGenerator protocol over the ModelRouter."""

    def __init__(self, router: ModelRouter, stage: str = "empathize") -> None:
        self.router = router
        self.stage = stage

    def _sliced_context(self, question: str, context: str) -> str:
        """Fusion delegation: the sidekick (cached corpus prefix) returns the
        relevant spans; the frontier turn only pays for the slices."""
        if len(context) <= DELEGATE_THRESHOLD_CHARS:
            return context
        outcome = self.router.invoke(
            "sidekick",
            "sidekick/context_query",
            stage=self.stage,  # type: ignore[arg-type]
            params={"context": context, "question": question},
            max_tokens=8000,
        )
        # Truncated retrieval still returned valid verbatim spans - use them.
        # Falling back to the full corpus would silently pay 100x the tokens.
        if outcome.status in ("ok", "truncated") and outcome.text.strip():
            return outcome.text
        return context

    def answer(
        self, persona: Persona, question: str, context: str
    ) -> GroundedAnswer | ProfileOpinion | Abstention:
        outcome = self.router.invoke(
            "research",
            "empathize/persona_turn",
            stage=self.stage,  # type: ignore[arg-type]
            params={
                "persona": dumps(persona.model_dump()),
                "context": self._sliced_context(question, context),
                "question": question,
            },
            schema=PersonaTurn,
        )
        if not outcome.ok or outcome.data is None:
            return Abstention(reason=f"model_unavailable: {outcome.status}")
        turn: PersonaTurn = outcome.data
        if turn.kind == "grounded" and turn.citations:
            return GroundedAnswer(text=turn.text, citations=turn.citations)
        if turn.kind == "opinion":
            return ProfileOpinion(text=turn.text)
        return Abstention(reason=turn.gap or "no grounding available")
