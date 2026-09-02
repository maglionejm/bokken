"""Scripted stage engines that satisfy each stage's exit criteria offline."""

from __future__ import annotations

from bokken.journal import Actor
from bokken.orchestrator import StageContext, StageOutcome

HUMAN = Actor(kind="human", name="founder")
AGENT = Actor(kind="agent", name="facilitator", model="fake")


def _persona(n: int) -> Actor:
    return Actor(kind="agent", name=f"panelist-{n}", model="fake", persona_id=f"p-{n}")


class EmpathizeFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        segments = ctx.state.brief.get("target_segments", [])
        for i, segment in enumerate(segments):
            if ctx.state.mode == "dojo":
                actor, confidence = _persona(i), "simulated"
            else:
                actor, confidence = HUMAN, "observed"
            ctx.store.append(
                type="evidence.captured",
                stage="empathize",
                actor=actor,
                payload={
                    "content": f"signal about {segment}",
                    "source": "interview",
                    "confidence_class": confidence,
                    "segment": segment,
                },
            )
        return None


class AskingEmpathizeFake(EmpathizeFake):
    """Founder-mode engine that needs a human answer before capturing evidence."""

    def run(self, ctx: StageContext) -> StageOutcome | None:
        answer = ctx.input_port.ask("Tell me about the last time this problem hit you.")
        segments = ctx.state.brief.get("target_segments", [])
        for segment in segments:
            ctx.store.append(
                type="evidence.captured",
                stage="empathize",
                actor=answer.actor,
                payload={
                    "content": answer.text,
                    "source": "interview",
                    "confidence_class": answer.confidence_class("observed"),
                    "segment": segment,
                },
            )
        return None


class DefineFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        evidence_ids = list(ctx.state.evidence)
        insight = ctx.store.append(
            type="interpretation.derived",
            stage="define",
            actor=AGENT,
            payload={"kind": "insight", "statement": "predictability beats speed"},
            refs=evidence_ids[:1],
        )
        ctx.store.append(
            type="decision.recorded",
            stage="define",
            actor=AGENT,
            payload={
                "question": "problem statement",
                "options": ["ps-a", "ps-b"],
                "criteria": ["evidence coverage"],
                "resolution": "ps-a",
                "dissent": [],
            },
            refs=[insight.id],
        )
        return None


class IdeateFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        option = ctx.store.append(
            type="option.created",
            stage="ideate",
            actor=AGENT,
            payload={"summary": "adaptive shuttle"},
        )
        ctx.store.append(
            type="decision.recorded",
            stage="ideate",
            actor=AGENT,
            payload={
                "question": "which concept advances",
                "options": [option.id],
                "criteria": ["dfv"],
                "resolution": option.id,
                "dissent": [],
            },
            refs=[option.id],
        )
        return None


class PrototypeFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        assumption = ctx.store.append(
            type="assumption.registered",
            stage="prototype",
            actor=AGENT,
            payload={"statement": "riders accept detours", "impact": "high", "uncertainty": "high"},
        )
        ctx.store.append(
            type="artifact.generated",
            stage="prototype",
            actor=AGENT,
            payload={
                "path": "artifacts/prototype/one-pager.md",
                "kind": "concept_one_pager",
                "content_hash": "h",
            },
            refs=[assumption.id],
        )
        return None


class TestFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        for assumption_id in ctx.state.assumptions:
            ctx.store.append(
                type="assumption.scored",
                stage="test",
                actor=AGENT,
                payload={"score": "supported"},
                refs=[assumption_id],
            )
        ctx.store.append(
            type="decision.recorded",
            stage="test",
            actor=AGENT,
            payload={
                "question": "kill, iterate, or proceed",
                "options": ["kill", "iterate", "proceed"],
                "criteria": ["assumption scores"],
                "resolution": "proceed",
                "dissent": [],
                "requires_real_validation": True,
            },
        )
        return None


class BurnBudgetFake:
    """Empathize engine that spends tokens without meeting criteria."""

    def run(self, ctx: StageContext) -> StageOutcome | None:
        ctx.store.append(
            type="model.called",
            stage="empathize",
            actor=AGENT,
            payload={
                "routing_class": "cognition",
                "model": "fake",
                "prompt_id": "x",
                "prompt_version": "v1",
                "prompt_hash": "h",
                "usage": {"input_tokens": 900, "output_tokens": 200},
                "status": "ok",
            },
        )
        return None


class NoopFake:
    def run(self, ctx: StageContext) -> StageOutcome | None:
        return None


def full_engine_suite() -> dict:
    return {
        "empathize": EmpathizeFake(),
        "define": DefineFake(),
        "ideate": IdeateFake(),
        "prototype": PrototypeFake(),
        "test": TestFake(),
    }
