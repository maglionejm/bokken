"""The Kata registry: named, parameterized, budgeted facilitation moves."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from bokken.journal import Actor, Event, JournalStore, SessionState, Stage
from bokken.kata.render import render_move

Signals = dict[str, Any]


@dataclass(frozen=True)
class TriggerFire:
    """A trigger that fired: what tripped it and the move's parameters."""

    trigger: str
    params: dict[str, Any] = field(default_factory=dict)
    refs: list[str] = field(default_factory=list)


Trigger = Callable[[SessionState, Signals], TriggerFire | None]


@dataclass(frozen=True)
class Move:
    move_id: str
    intent: str
    stages: frozenset[Stage]
    trigger: Trigger
    trigger_description: str
    surfaces: dict[str, str]  # mode -> how the move manifests on that surface
    default_budget: int | None  # max executions per session; None = unlimited


class UnknownMoveError(Exception):
    pass


class Kata:
    """Evaluates move triggers against state + engine signals; executes or
    suppresses, always journaling the outcome."""

    def __init__(
        self,
        moves: Iterable[Move],
        store: JournalStore,
        *,
        budgets: dict[str, int] | None = None,
        actor: Actor | None = None,
    ) -> None:
        self._moves = {m.move_id: m for m in moves}
        self._store = store
        self._actor = actor or Actor(kind="agent", name="facilitator")
        # Per-session budgets may tighten but never exceed the registry maximum.
        self._budgets: dict[str, int | None] = {}
        for move in self._moves.values():
            override = (budgets or {}).get(move.move_id)
            if override is None:
                self._budgets[move.move_id] = move.default_budget
            elif move.default_budget is None:
                self._budgets[move.move_id] = override
            else:
                self._budgets[move.move_id] = min(override, move.default_budget)

    def list_moves(self) -> list[Move]:
        return sorted(self._moves.values(), key=lambda m: m.move_id)

    def budget(self, move_id: str) -> int | None:
        return self._budgets[move_id]

    def evaluate(
        self,
        move_id: str,
        state: SessionState,
        signals: Signals,
        *,
        stage: Stage,
        mode: str = "founder",
    ) -> Event | None:
        """Evaluate one move. Returns the journaled executed/suppressed event,
        or None when the trigger did not fire."""
        move = self._moves.get(move_id)
        if move is None:
            raise UnknownMoveError(move_id)
        fire = move.trigger(state, signals)
        if fire is None:
            return None
        if stage not in move.stages:
            return self._suppress(move, fire, stage, "out_of_stage")
        budget = self._budgets[move_id]
        if budget is not None and state.moves_executed.get(move_id, 0) >= budget:
            return self._suppress(move, fire, stage, "budget_exhausted")
        rendered = render_move(move_id, fire, mode)
        return self._store.append(
            type="facilitation.move_executed",
            stage=stage,
            actor=self._actor,
            payload={
                "move_id": move_id,
                "trigger": fire.trigger,
                "params": fire.params,
                "outcome": rendered,
            },
            refs=fire.refs,
        )

    def _suppress(self, move: Move, fire: TriggerFire, stage: Stage, reason: str) -> Event:
        return self._store.append(
            type="facilitation.move_suppressed",
            stage=stage,
            actor=self._actor,
            payload={"move_id": move.move_id, "trigger": fire.trigger, "reason": reason},
            refs=fire.refs,
        )
