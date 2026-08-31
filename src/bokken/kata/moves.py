"""The MVP move set.

Triggers are pure functions over (SessionState, Signals). Structural moves fire
on state/signal facts the engines compute (counts, rates, flags). Moves needing
semantic judgment (hmw_reframe, assumption_flag, loopback_proposal, ...) fire
only when an engine supplies the corresponding signal - typically produced via
the Judge seam - so they stay inert without one.
"""

from __future__ import annotations

from bokken.journal import SessionState, Stage
from bokken.kata.registry import Move, Signals, TriggerFire

_ALL_WORK_STAGES: frozenset[Stage] = frozenset(
    {"empathize", "define", "ideate", "prototype", "test"}
)


def _stage_contract(state: SessionState, signals: Signals) -> TriggerFire | None:
    if not signals.get("stage_opened"):
        return None
    return TriggerFire(
        trigger="stage entry",
        params={
            "stage": signals.get("stage", state.stage),
            "goal": signals.get("goal", ""),
            "method": signals.get("method", ""),
            "exit_bar": signals.get("exit_bar", ""),
        },
    )


def _hmw_reframe(state: SessionState, signals: Signals) -> TriggerFire | None:
    statement = signals.get("solution_shaped_statement")
    if not statement:
        return None
    return TriggerFire(
        trigger="problem statement is solution-shaped",
        params={"statement": statement, "reframe": signals.get("reframe", "...")},
        refs=list(signals.get("refs", [])),
    )


def _assumption_flag(state: SessionState, signals: Signals) -> TriggerFire | None:
    claim = signals.get("unsupported_claim")
    if not claim:
        return None
    return TriggerFire(
        trigger="unsupported quantified claim",
        params={"claim": claim},
        refs=list(signals.get("refs", [])),
    )


def _timebox_pivot(state: SessionState, signals: Signals) -> TriggerFire | None:
    rate = signals.get("novelty_rate")
    floor = signals.get("novelty_floor", state.config.get("budgets", {}).get("novelty_floor"))
    if rate is None or floor is None or rate >= floor:
        return None
    return TriggerFire(
        trigger="idea novelty rate below floor",
        params={"novelty_rate": rate, "floor": floor},
    )


def _synthesis_readback(state: SessionState, signals: Signals) -> TriggerFire | None:
    if not signals.get("stage_exiting"):
        return None
    return TriggerFire(
        trigger="stage exit",
        params={"synthesis": signals.get("synthesis", "")},
        refs=list(signals.get("refs", [])),
    )


def _devils_advocate(state: SessionState, signals: Signals) -> TriggerFire | None:
    if not signals.get("consensus_without_dissent"):
        return None
    return TriggerFire(
        trigger="consensus reached with zero dissent",
        params={"counter": signals.get("counter", "")},
        refs=list(signals.get("refs", [])),
    )


def _parking_lot(state: SessionState, signals: Signals) -> TriggerFire | None:
    topic = signals.get("offscope_topic")
    if not topic:
        return None
    return TriggerFire(trigger="off-scope thread persisting", params={"topic": topic})


def _loopback_proposal(state: SessionState, signals: Signals) -> TriggerFire | None:
    contradiction = signals.get("contradiction")
    if not contradiction:
        return None
    return TriggerFire(
        trigger="test/define contradiction detected",
        params={
            "contradiction": contradiction,
            "target_stage": signals.get("target_stage", "define"),
        },
        refs=list(signals.get("refs", [])),
    )


def _close_and_commit(state: SessionState, signals: Signals) -> TriggerFire | None:
    if not signals.get("run_ending"):
        return None
    return TriggerFire(
        trigger="final phase of the run",
        params={"commitments": signals.get("commitments", "")},
    )


MVP_MOVES: tuple[Move, ...] = (
    Move(
        move_id="stage_contract",
        intent="Open a stage by stating goal, method, and exit bar",
        stages=_ALL_WORK_STAGES,
        trigger=_stage_contract,
        trigger_description="stage entry (engine signals stage_opened)",
        surfaces={"founder": "stage banner prompt", "dojo": "panel briefing preamble"},
        default_budget=None,
    ),
    Move(
        move_id="hmw_reframe",
        intent="Reframe a solution-shaped problem statement as a How Might We",
        stages=frozenset({"define"}),
        trigger=_hmw_reframe,
        trigger_description="judge-detected solution-shaped statement signal",
        surfaces={"founder": "reframing prompt", "dojo": "autonomous reframe"},
        default_budget=None,
    ),
    Move(
        move_id="assumption_flag",
        intent="Mark an unsupported quantified claim as unvalidated",
        stages=_ALL_WORK_STAGES,
        trigger=_assumption_flag,
        trigger_description="judge-detected unsupported claim signal",
        surfaces={"founder": "inline flag", "dojo": "register entry"},
        default_budget=None,
    ),
    Move(
        move_id="timebox_pivot",
        intent="Propose moving from divergence to convergence on novelty decay",
        stages=frozenset({"ideate"}),
        trigger=_timebox_pivot,
        trigger_description="novelty_rate below the configured floor",
        surfaces={"founder": "pivot proposal prompt", "dojo": "autonomous pivot"},
        default_budget=3,
    ),
    Move(
        move_id="synthesis_readback",
        intent="Read back what was heard at stage exit and invite correction",
        stages=_ALL_WORK_STAGES,
        trigger=_synthesis_readback,
        trigger_description="stage_exiting signal",
        surfaces={"founder": "readback prompt", "dojo": "journaled synthesis"},
        default_budget=None,
    ),
    Move(
        move_id="devils_advocate",
        intent="Inject a labeled counter-position when consensus forms without dissent",
        stages=frozenset({"define", "ideate", "test"}),
        trigger=_devils_advocate,
        trigger_description="consensus_without_dissent signal",
        surfaces={"founder": "counter-position prompt", "dojo": "skeptic reinforcement"},
        default_budget=3,
    ),
    Move(
        move_id="parking_lot",
        intent="Park an off-scope thread visibly",
        stages=_ALL_WORK_STAGES,
        trigger=_parking_lot,
        trigger_description="offscope_topic signal persisting",
        surfaces={"founder": "parking note", "dojo": "journaled parking"},
        default_budget=None,
    ),
    Move(
        move_id="loopback_proposal",
        intent="Propose returning to an earlier stage on contradiction",
        stages=frozenset({"test", "define"}),
        trigger=_loopback_proposal,
        trigger_description="contradiction signal with target stage",
        surfaces={"founder": "loop-back proposal prompt", "dojo": "gated loop-back proposal"},
        default_budget=None,
    ),
    Move(
        move_id="close_and_commit",
        intent="Extract binding commitments with owners at run end",
        stages=frozenset({"test", "complete"}),
        trigger=_close_and_commit,
        trigger_description="run_ending signal",
        surfaces={"founder": "commitment prompt", "dojo": "dossier commitments section"},
        default_budget=1,
    ),
)
