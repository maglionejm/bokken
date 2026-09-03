"""Router-backed persona turn generation for Dojo interviews and evaluations."""

from __future__ import annotations

import hashlib

from bokken.models.router import Attributed, ModelRouter
from bokken.panel import Abstention, GroundedAnswer, Persona, ProfileOpinion
from bokken.panel.grounding import PersonaTurn
from bokken.stages.base import dumps
from bokken.stages.schemas import PersonaTurn as TurnPayload

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

    def answer(self, persona: Persona, question: str, context: str) -> PersonaTurn:
        outcome = self.router.invoke(
            "research",
            "empathize/persona_turn",
            stage=self.stage,  # type: ignore[arg-type]
            params={
                "persona": dumps(persona.model_dump()),
                "context": self._sliced_context(question, context),
                "question": question,
            },
            schema=TurnPayload,
        )
        # The attribution rides along either way: the model that answered on a
        # good turn, and on a failed one the model the failed call reached for.
        if not outcome.ok or outcome.data is None:
            return Attributed(
                data=Abstention(reason=f"model_unavailable: {outcome.status}"),
                attribution=outcome.attribution,
            )
        turn: TurnPayload = outcome.data
        result: GroundedAnswer | ProfileOpinion | Abstention
        if turn.kind == "grounded" and turn.citations:
            result = GroundedAnswer(text=turn.text, citations=turn.citations)
        elif turn.kind == "opinion":
            result = ProfileOpinion(text=turn.text)
        else:
            result = Abstention(reason=turn.gap or "no grounding available")
        return Attributed(data=result, attribution=outcome.attribution)
