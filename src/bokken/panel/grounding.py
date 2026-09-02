"""Grounded persona turns: answer from the corpus with citations, or abstain."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from bokken.journal import Event, JournalStore, Stage
from bokken.panel.casting import Persona
from bokken.panel.corpus import Citation, Corpus


class GroundedAnswer(BaseModel):
    text: str
    citations: list[Citation] = Field(min_length=1)


class ProfileOpinion(BaseModel):
    """A preference/opinion derived from the persona profile, not the corpus."""

    text: str


class Abstention(BaseModel):
    reason: str


class PersonaTurnGenerator(Protocol):
    model: str  # the model serving these turns, for journal provenance

    def answer(
        self, persona: Persona, question: str, context: str
    ) -> GroundedAnswer | ProfileOpinion | Abstention: ...


class Interviewer:
    """Runs persona turns with the grounding backstop: every citation is
    re-validated against the corpus; invalid citations become abstentions."""

    def __init__(
        self, corpus: Corpus, generator: PersonaTurnGenerator, store: JournalStore
    ) -> None:
        self.corpus = corpus
        self.generator = generator
        self.store = store

    def ask(
        self,
        persona: Persona,
        question: str,
        *,
        stage: Stage,
        segment: str | None = None,
    ) -> Event:
        context = self.corpus.context_for(persona.grounding_scope or None)
        result = self.generator.answer(persona, question, context)

        if isinstance(result, GroundedAnswer):
            invalid = [c for c in result.citations if not self.corpus.validate_citation(c)]
            if invalid:
                result = Abstention(
                    reason=f"citation_invalid: {len(invalid)} citation(s) did not "
                    "resolve to a corpus span"
                )
            else:
                return self.store.append(
                    type="evidence.captured",
                    stage=stage,
                    actor=persona.actor(self.generator.model),
                    payload={
                        "content": result.text,
                        "source": f"persona:{persona.persona_id}",
                        "confidence_class": "simulated",
                        "speaker": persona.name,
                        "segment": segment or persona.segment,
                        "grounding": "corpus",
                        "citations": [
                            {**c.model_dump(), "source_kind": self.corpus.kind_of(c.source_id)}
                            for c in result.citations
                        ],
                    },
                )

        if isinstance(result, ProfileOpinion):
            return self.store.append(
                type="evidence.captured",
                stage=stage,
                actor=persona.actor(self.generator.model),
                payload={
                    "content": result.text,
                    "source": f"persona:{persona.persona_id}",
                    "confidence_class": "simulated",
                    "speaker": persona.name,
                    "segment": segment or persona.segment,
                    "grounding": "profile",
                    "citations": [],
                },
            )

        return self.store.append(
            type="evidence.abstained",
            stage=stage,
            actor=persona.actor(self.generator.model),
            payload={
                "question": question,
                "gap": result.reason,
                "segment": segment or persona.segment,
            },
        )
