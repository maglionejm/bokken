"""Router-backed persona turn generation for Dojo interviews and evaluations."""

from __future__ import annotations

from bokken.models.router import ModelRouter
from bokken.panel import Abstention, GroundedAnswer, Persona, ProfileOpinion
from bokken.stages.base import dumps
from bokken.stages.schemas import PersonaTurn


class RouterTurnGenerator:
    """Implements the panel's PersonaTurnGenerator protocol over the ModelRouter."""

    def __init__(self, router: ModelRouter, stage: str = "empathize") -> None:
        self.router = router
        self.stage = stage

    def answer(
        self, persona: Persona, question: str, context: str
    ) -> GroundedAnswer | ProfileOpinion | Abstention:
        outcome = self.router.invoke(
            "cognition",
            "empathize/persona_turn",
            stage=self.stage,  # type: ignore[arg-type]
            params={
                "persona": dumps(persona.model_dump()),
                "context": context,
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
