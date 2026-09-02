"""Router-backed persona turn generation for Dojo interviews and evaluations."""

from __future__ import annotations

import hashlib

from bokken.models.router import ModelRouter
from bokken.panel import Abstention, GroundedAnswer, Persona, ProfileOpinion
from bokken.stages.base import dumps
from bokken.stages.schemas import PersonaTurn

# Below this, slicing costs more than it saves. The persona turn now caches its
# corpus prefix across the whole interview, so an undelegated corpus is paid for
# once at the write premium and read back at a tenth of fresh input; delegation
# has to beat that, and it carries the sidekick's own retrieval output at
# frontier output prices on every question. That break-even sits far above the
# 20k chars this threshold used before the corpus was cacheable.
DELEGATE_THRESHOLD_CHARS = 120_000


class RouterTurnGenerator:
    """Implements the panel's PersonaTurnGenerator protocol over the ModelRouter."""

    def __init__(self, router: ModelRouter, stage: str = "empathize") -> None:
        self.router = router
        self.stage = stage
        self.model = router.routing["research"]  # persona turns run on research
        self._slices: dict[str, str] = {}

    def _sliced_context(self, question: str, context: str) -> str:
        """Fusion delegation: the sidekick (cached corpus prefix) returns the
        relevant spans; the frontier turn only pays for the slices.

        Retrieval is memoized per (question, corpus). Every persona on a panel
        asks the identical question over the identical corpus, so re-invoking the
        sidekick would pay for the same retrieval N times and - because the model
        need not answer identically - would hand each persona turn a different
        corpus prefix, turning its cache block into N writes and no reads.
        """
        threshold = DELEGATE_THRESHOLD_CHARS
        if len(context) <= threshold:
            return context
        key = hashlib.sha256(f"{len(question)}:{question}{context}".encode()).hexdigest()
        if key in self._slices:
            return self._slices[key]
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
            self._slices[key] = outcome.text
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
