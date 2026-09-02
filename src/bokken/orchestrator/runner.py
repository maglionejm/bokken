"""Session runner: create/run/step/stop over the journal, with gates and budgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import uuid4

from bokken.journal import (
    Actor,
    Brief,
    JournalStore,
    Mode,
    SessionState,
    Stage,
    create_session_dir,
    replay,
    resolve_session_dir,
)
from bokken.orchestrator.machine import (
    FORWARD,
    CriteriaVerdict,
    IllegalTransitionError,
    can_exit,
    is_legal,
    is_loopback,
    justification_refs,
)

SYSTEM_ACTOR = Actor(kind="system", name="orchestrator")

GatePolicy = Literal["none", "stage_boundaries"] | list[str]
HaltKind = Literal["completed", "gate_pending", "input_pending", "stopped", "stepped"]

# Config keys a human may override on resume. Everything else is immutable
# after creation (no-silent-self-escalation: the brief, gate policy, and
# success criteria can never change; budgets only by an explicit human action).
_OVERRIDABLE_CONFIG_KEYS = frozenset({"budgets"})


class OrchestratorError(Exception):
    pass


class MissingEngineError(OrchestratorError):
    pass


class StalledStageError(OrchestratorError):
    pass


class NoPendingGateError(OrchestratorError):
    pass


class SelfEscalationError(OrchestratorError):
    pass


class InputRequired(Exception):
    """Raised by an input port that cannot answer interactively right now."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__(question)


class InputPort(Protocol):
    def ask(self, question: str, *, kind: str = "text") -> str: ...


class NoInputPort:
    """Input port for headless runs: any question halts the run as input_pending."""

    def ask(self, question: str, *, kind: str = "text") -> str:
        raise InputRequired(question)


@dataclass(frozen=True)
class StageOutcome:
    """What a stage engine reports back. Forward progress is never proposed here —
    it is derived from exit criteria; only loop-backs are engine-proposed."""

    loopback_to: Stage | None = None
    condition: str = ""
    refs: list[str] = field(default_factory=list)


@dataclass
class StageContext:
    state: SessionState
    store: JournalStore
    input_port: InputPort
    kata: Any | None = None
    actor: Actor = field(default_factory=lambda: SYSTEM_ACTOR)


class StageEngine(Protocol):
    def run(self, ctx: StageContext) -> StageOutcome | None: ...


@dataclass(frozen=True)
class RunResult:
    halt: HaltKind
    stage: Stage
    detail: str = ""
    pending_question: str | None = None


def default_config(mode: Mode, gate_policy: GatePolicy | None, budgets: dict | None) -> dict:
    if gate_policy is None:
        gate_policy = "stage_boundaries" if mode == "dojo" else "none"
    return {
        "gate_policy": gate_policy,
        "budgets": {"total_tokens": None, "novelty_floor": None, **(budgets or {})},
    }


def create_session(
    name: str,
    *,
    brief: dict[str, Any] | Brief,
    mode: Mode,
    gate_policy: GatePolicy | None = None,
    budgets: dict[str, Any] | None = None,
    config_extra: dict[str, Any] | None = None,
    base: Path | None = None,
) -> Path:
    """Validate the brief and journal session.created; the session starts in intake."""
    validated = brief if isinstance(brief, Brief) else Brief.model_validate(brief)
    import bokken

    config = default_config(mode, gate_policy, budgets) | (config_extra or {})
    # Reproducibility: every journal knows which Bokken created it.
    config["bokken_version"] = bokken.__version__
    session_dir = create_session_dir(name, base=base)
    with JournalStore.open(session_dir) as store:
        store.append(
            type="session.created",
            stage="intake",
            actor=SYSTEM_ACTOR,
            payload={
                "name": name,
                "mode": mode,
                "brief": validated.model_dump(),
                "config": config,
            },
        )
    return session_dir


def _gate_required(policy: GatePolicy, from_stage: Stage) -> bool:
    if policy == "none":
        return False
    if policy == "stage_boundaries":
        return True
    return from_stage in policy


class Runner:
    """Drives one session's loop. Holds the session write lock only while running."""

    def __init__(
        self,
        session_dir: Path,
        *,
        engines: dict[Stage, StageEngine] | None = None,
        input_port: InputPort | None = None,
        kata_factory: Any | None = None,
    ) -> None:
        self.session_dir = session_dir
        self.engines = engines or {}
        self.input_port = input_port or NoInputPort()
        self.kata_factory = kata_factory

    @classmethod
    def for_session(cls, name: str, base: Path | None = None, **kw: Any) -> Runner:
        return cls(resolve_session_dir(name, base=base), **kw)

    # -- lifecycle ---------------------------------------------------------

    def run(
        self,
        *,
        max_transitions: int | None = None,
        config_overrides: dict[str, Any] | None = None,
        actor: Actor = SYSTEM_ACTOR,
    ) -> RunResult:
        with JournalStore.open(self.session_dir) as store:
            state = replay(store.events())
            if store.last_seq > 1:
                overrides = self._vet_overrides(store, state, config_overrides, actor)
                payload: dict[str, Any] = {}
                if overrides:
                    payload["config_overrides"] = overrides
                store.append(
                    type="session.resumed", stage=state.stage, actor=actor, payload=payload
                )
            elif config_overrides:
                raise SelfEscalationError("config overrides are only valid when resuming")
            return self._loop(store, max_transitions)

    def step(self, **kw: Any) -> RunResult:
        return self.run(max_transitions=1, **kw)

    def stop(self, *, actor: Actor, detail: str | None = None) -> None:
        with JournalStore.open(self.session_dir) as store:
            state = replay(store.events())
            store.append(
                type="session.stopped",
                stage=state.stage,
                actor=actor,
                payload={"reason": "human_stop", "detail": detail},
            )

    def resolve_gate(
        self, *, resolution: Literal["approve", "reject"], actor: Actor, reason: str | None = None
    ) -> None:
        with JournalStore.open(self.session_dir) as store:
            state = replay(store.events())
            if state.pending_gate is None:
                raise NoPendingGateError("no gate is pending for this session")
            store.append(
                type="session.gate_resolved",
                stage=state.stage,
                actor=actor,
                payload={
                    "gate_id": state.pending_gate.gate_id,
                    "resolution": resolution,
                    "reason": reason,
                },
            )

    def request_loopback(self, *, to_stage: Stage, reason: str, actor: Actor) -> None:
        with JournalStore.open(self.session_dir) as store:
            state = replay(store.events())
            if not is_loopback(state.stage, to_stage):
                raise IllegalTransitionError(state.stage, to_stage)
            store.append(
                type="transition.fired",
                stage=state.stage,
                actor=actor,
                payload={
                    "from_stage": state.stage,
                    "to_stage": to_stage,
                    "condition": f"human loop-back: {reason}",
                },
            )

    # -- internals ---------------------------------------------------------

    def _vet_overrides(
        self,
        store: JournalStore,
        state: SessionState,
        overrides: dict[str, Any] | None,
        actor: Actor,
    ) -> dict[str, Any] | None:
        if not overrides:
            return None
        illegal_keys = set(overrides) - _OVERRIDABLE_CONFIG_KEYS
        if actor.kind != "human" or illegal_keys:
            what = "non-human actor" if actor.kind != "human" else f"keys {sorted(illegal_keys)}"
            store.append(
                type="facilitation.move_suppressed",
                stage=state.stage,
                actor=actor,
                payload={
                    "move_id": "config_change_attempt",
                    "trigger": f"config override refused: {what}",
                    "reason": "mode_config",
                },
            )
            raise SelfEscalationError(
                f"config override refused ({what}); the brief, gate policy, and "
                "success criteria are immutable, and budgets change only by human action"
            )
        return overrides

    # An engine may legitimately need a few passes over a stage, but a stage whose
    # exit criteria never become satisfiable (e.g. no evidence exists to ground an
    # insight) must fail loudly instead of looping forever.
    MAX_ENGINE_ATTEMPTS_PER_STAGE = 4

    def _loop(self, store: JournalStore, max_transitions: int | None) -> RunResult:
        transitions = 0
        engine_attempts: dict[Stage, int] = {}
        while True:
            state = replay(store.events())
            if state.stage == "complete":
                return RunResult("completed", state.stage)
            if state.pending_gate is not None:
                gate = state.pending_gate
                return RunResult(
                    "gate_pending",
                    state.stage,
                    detail=f"gate {gate.gate_id} guards {gate.from_stage} -> {gate.to_stage}",
                )
            if state.stopped is not None:
                return RunResult("stopped", state.stage, detail=state.stopped)
            if self._budget_exhausted(state):
                store.append(
                    type="session.stopped",
                    stage=state.stage,
                    actor=SYSTEM_ACTOR,
                    payload={"reason": "budget_exhausted", "detail": "token budget spent"},
                )
                return RunResult("stopped", state.stage, detail="budget_exhausted")
            if max_transitions is not None and transitions >= max_transitions:
                return RunResult("stepped", state.stage)

            if state.approved_gate is not None and state.approved_gate.from_stage == state.stage:
                self._fire(store, state, state.approved_gate.to_stage, "gate approved")
                transitions += 1
                continue

            verdict = can_exit(state.stage, state)
            if verdict.ok and not self._rework_pending(state):
                if self._maybe_request_gate(store, state):
                    continue  # loop re-reads state and halts on the pending gate
                self._fire(store, state, FORWARD[state.stage], "exit criteria met")
                transitions += 1
                continue

            engine_attempts[state.stage] = engine_attempts.get(state.stage, 0) + 1
            if engine_attempts[state.stage] > self.MAX_ENGINE_ATTEMPTS_PER_STAGE:
                raise StalledStageError(
                    f"engine for {state.stage} ran {engine_attempts[state.stage] - 1} times "
                    f"without meeting the exit criteria; unmet: {verdict.unmet}"
                )
            result = self._run_engine(store, state, verdict)
            if result is not None:
                return result

    @staticmethod
    def _rework_pending(state: SessionState) -> bool:
        """A fresh loop-back means rework: the target stage's engine must run at
        least once before exit criteria may fast-forward the session again."""
        if not state.transitions:
            return False
        last = state.transitions[-1]
        return is_loopback(last["from"], last["to"]) and state.events_since_transition == 0

    def _budget_exhausted(self, state: SessionState) -> bool:
        total = state.config.get("budgets", {}).get("total_tokens")
        return total is not None and state.tokens_spent() >= total

    def _maybe_request_gate(self, store: JournalStore, state: SessionState) -> bool:
        policy = state.config.get("gate_policy", "none")
        if not _gate_required(policy, state.stage):
            return False
        store.append(
            type="session.gate_requested",
            stage=state.stage,
            actor=SYSTEM_ACTOR,
            payload={
                "gate_id": f"g-{uuid4().hex[:8]}",
                "from_stage": state.stage,
                "to_stage": FORWARD[state.stage],
            },
        )
        return True

    def _fire(
        self,
        store: JournalStore,
        state: SessionState,
        to_stage: Stage,
        condition: str,
        refs: list[str] | None = None,
    ) -> None:
        if not is_legal(state.stage, to_stage):
            raise IllegalTransitionError(state.stage, to_stage)
        store.append(
            type="transition.fired",
            stage=state.stage,
            actor=SYSTEM_ACTOR,
            payload={"from_stage": state.stage, "to_stage": to_stage, "condition": condition},
            refs=refs if refs is not None else justification_refs(state.stage, state),
        )

    def _run_engine(
        self, store: JournalStore, state: SessionState, verdict: CriteriaVerdict
    ) -> RunResult | None:
        engine = self.engines.get(state.stage)
        if engine is None:
            raise MissingEngineError(
                f"stage {state.stage} has unmet criteria and no engine: {verdict.unmet}"
            )
        kata = self.kata_factory(store) if self.kata_factory else None
        ctx = StageContext(state=state, store=store, input_port=self.input_port, kata=kata)
        seq_before = store.last_seq
        try:
            outcome = engine.run(ctx)
        except InputRequired as pending:
            return RunResult(
                "input_pending",
                state.stage,
                detail="waiting for human input",
                pending_question=pending.question,
            )
        if outcome is not None and outcome.loopback_to is not None:
            fresh = replay(store.events())
            if not is_loopback(fresh.stage, outcome.loopback_to):
                raise IllegalTransitionError(fresh.stage, outcome.loopback_to)
            self._fire(store, fresh, outcome.loopback_to, outcome.condition, outcome.refs)
            return None
        if store.last_seq == seq_before and not can_exit(state.stage, replay(store.events())).ok:
            raise StalledStageError(
                f"engine for {state.stage} made no progress; unmet: {verdict.unmet}"
            )
        return None
