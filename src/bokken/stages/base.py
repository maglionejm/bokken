"""Shared plumbing for stage engines."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from bokken.journal import Actor, JournalStore, RoutingClass, Stage
from bokken.models.router import ModelRouter
from bokken.orchestrator import SYSTEM_ACTOR, StageContext
from bokken.panel.corpus import Corpus

FOUNDER = Actor(kind="human", name="founder")


def facilitator(router: ModelRouter) -> Actor:
    """Stage mechanics run on the cognition lane; provenance follows routing."""
    return router.actor("facilitator", "cognition")


RouterFactory = Callable[[JournalStore], ModelRouter]


class StageError(Exception):
    """A model call failed in a way the engine cannot work around."""


def structured[T: BaseModel](
    router: ModelRouter,
    routing_class: RoutingClass,
    prompt_id: str,
    schema: type[T],
    *,
    stage: Stage,
    params: dict[str, Any],
) -> T | None:
    """Invoke and validate. Returns None on budget exhaustion (engine should
    return early and let the orchestrator stop the run); raises on error/refusal."""
    outcome = router.invoke(routing_class, prompt_id, stage=stage, params=params, schema=schema)
    if outcome.status == "budget_exhausted":
        return None
    if not outcome.ok or outcome.data is None:
        raise StageError(f"{prompt_id} failed: {outcome.status} {outcome.detail}")
    return outcome.data


def journal_rejected_inputs(store: JournalStore, corpus: Corpus, *, stage: Stage) -> None:
    """A declared input the corpus refused or skipped is a grounding gap on the
    record, never a silent omission."""
    for skipped in corpus.skipped:
        store.append(
            type="evidence.input_rejected",
            stage=stage,
            actor=SYSTEM_ACTOR,
            payload={"path": skipped.path, "reason": skipped.reason},
        )


def open_stage(ctx: StageContext, *, goal: str, method: str, exit_bar: str) -> None:
    """Fire the stage_contract move once per stage entry."""
    if ctx.kata is None:
        return
    stage = ctx.state.stage
    if ctx.state.moves_by_stage.get(stage, {}).get("stage_contract"):
        return
    ctx.kata.evaluate(
        "stage_contract",
        ctx.state,
        {
            "stage_opened": True,
            "stage": stage,
            "goal": goal,
            "method": method,
            "exit_bar": exit_bar,
        },
        stage=stage,
        mode=ctx.state.mode or "founder",
    )


def opportunities_text(state) -> str:
    """The Ulwick ranking journaled by Empathize, as prompt-ready lines."""
    records = [i for i in state.insights.values() if i.kind == "opportunity"]
    if not records:
        return "(no opportunity ranking on file)"
    return "\n".join(f"- {r.statement}" for r in records)


def evidence_lines(store: JournalStore) -> str:
    """Render captured evidence as '- id: content' lines for clustering prompts."""
    lines = []
    for event in store.events():
        if event.type == "evidence.captured":
            lines.append(f"- {event.id}: {event.payload['content']}")
    return "\n".join(lines)


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)
