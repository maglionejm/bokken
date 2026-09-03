"""Session runner: create/run/step/stop over the journal, with gates and budgets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import uuid4

from bokken.journal import (
    Actor,
    Brief,
    ConfidenceClass,
    Event,
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
GATE_POLICY_LITERALS: frozenset[str] = frozenset({"none", "stage_boundaries"})
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


class GatePolicyError(OrchestratorError):
    """The declared gate policy is not one the orchestrator recognizes.

    Gates are the mechanism that keeps an autonomous run under human control,
    so an unreadable policy fails closed and loudly. It is never interpreted as
    "no gates": a typo would otherwise disable every gate in the run silently.
    """


class InputRequired(Exception):
    """Raised by an input port that cannot answer interactively right now."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__(question)


@dataclass(frozen=True)
class Answer:
    """An answer plus the provenance of whoever actually supplied it.

    Ports return this instead of a bare string so that every record derived
    from an answer is attributed to its real author — the human at the
    terminal, or the agent client that submitted it over MCP — rather than to
    an assumed human founder. Provenance is not optional: ``actor`` has no
    default, so no port can hand a stage an unattributed answer.
    """

    text: str
    actor: Actor

    @property
    def is_human(self) -> bool:
        return self.actor.kind == "human"

    def confidence_class(self, human_class: ConfidenceClass) -> ConfidenceClass:
        """The class to journal: a human answer keeps the call site's class; a
        machine-supplied one is `simulated` at the record level (honesty rules —
        synthetic contributions are never laundered into human testimony)."""
        return human_class if self.is_human else "simulated"

    def source(self, human_source: str) -> str:
        """Source label to journal; a machine-supplied answer never reads as
        human testimony."""
        return human_source if self.is_human else f"agent-supplied ({self.actor.name})"


class InputPort(Protocol):
    def ask(self, question: str, *, kind: str = "text") -> Answer: ...


class NoInputPort:
    """Input port for headless runs: any question halts the run as input_pending."""

    def ask(self, question: str, *, kind: str = "text") -> Answer:
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


# -- gate policy -----------------------------------------------------------


def default_gate_policy(mode: Mode | None) -> GatePolicy:
    """The policy a run gets when it declares none. Only a founder run — which
    has a human at the terminal throughout — defaults to no gates."""
    return "none" if mode == "founder" else "stage_boundaries"


def normalize_gate_policy(policy: object) -> GatePolicy:
    """Validate a declared gate policy, or refuse it.

    The only legal forms are ``"none"``, ``"stage_boundaries"``, and a list of
    stage names that have a forward exit to gate. Anything else is refused:
    a typo'd literal (``"stage_boundary"``) or a comma-joined string must never
    fall through to a membership test, which would read as "gate no stage at
    all" and take an autonomous run from intake to complete unsupervised.
    """
    if isinstance(policy, str):
        if policy in GATE_POLICY_LITERALS:
            return policy  # type: ignore[return-value]
        raise GatePolicyError(
            f"unknown gate policy {policy!r}; expected 'none', 'stage_boundaries', "
            f"or a list of stage names ({', '.join(FORWARD)})"
        )
    if isinstance(policy, list | tuple):
        stages = [str(stage) for stage in policy]
        unknown = [stage for stage in stages if stage not in FORWARD]
        if unknown:
            raise GatePolicyError(
                f"gate policy names {unknown} which are not gateable stages; "
                f"expected any of ({', '.join(FORWARD)})"
            )
        return stages
    raise GatePolicyError(
        "gate policy must be 'none', 'stage_boundaries', or a list of stage names, "
        f"got {type(policy).__name__}"
    )


def resolve_gate_policy(state: SessionState) -> GatePolicy:
    """The run's gate policy, validated before the run does any work.

    A journal that declares no policy is not a journal with no gates: an
    undeclared policy resolves from the mode exactly as creation resolves it.
    """
    if "gate_policy" not in state.config:
        return default_gate_policy(state.mode)
    return normalize_gate_policy(state.config["gate_policy"])


def gate_required(policy: GatePolicy, from_stage: Stage) -> bool:
    """Does leaving ``from_stage`` forward need a human approval first?

    ``policy`` must already be through :func:`normalize_gate_policy`, so the
    membership test below can only ever run against a list of real stage names.
    """
    if policy == "none":
        return False
    if policy == "stage_boundaries":
        return True
    return from_stage in policy


def default_config(mode: Mode, gate_policy: GatePolicy | None, budgets: dict | None) -> dict:
    return {
        "gate_policy": (
            default_gate_policy(mode) if gate_policy is None else normalize_gate_policy(gate_policy)
        ),
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
    # ``config_extra`` merges over the defaults and may carry its own
    # gate_policy, so the merged value — not just the argument — is what has to
    # be legal. A bad policy is refused here, before anything is journaled.
    config["gate_policy"] = (
        default_gate_policy(mode)
        if config.get("gate_policy") is None
        else normalize_gate_policy(config["gate_policy"])
    )
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


# -- loop predicates -------------------------------------------------------
#
# The run loop is a sequence of decisions; each decision lives here, named and
# testable on its own, rather than inline where it is too small to notice.

# Records that count as an engine's substantive work. Deliberately an
# allowlist of the domain families a stage's exit criteria are grounded in,
# plus a facilitation move that actually happened: a record type nobody has
# classified must not silently discharge a human's loop-back, and the stall
# guard turns that omission into a loud failure instead of a quiet skip.
SUBSTANTIVE_FAMILIES: frozenset[str] = frozenset(
    {"evidence", "interpretation", "option", "decision", "assumption", "artifact"}
)
# Exceptions inside those families that record a gap rather than work.
NON_SUBSTANTIVE_TYPES: frozenset[str] = frozenset({"evidence.input_rejected"})


def is_substantive_work(event_type: str) -> bool:
    """Does this record show an engine doing work, rather than bookkeeping?

    ``session.*`` and ``transition.fired`` are the runner's own bookkeeping.
    ``model.called`` is per-call telemetry: a refused or errored call is not a
    contribution, and even a successful one only becomes work once the engine
    journals what it produced. A suppressed facilitation move is a move that
    did not happen, and ``evidence.input_rejected`` is a grounding gap.
    """
    if event_type in NON_SUBSTANTIVE_TYPES:
        return False
    family = event_type.split(".", 1)[0]
    return family in SUBSTANTIVE_FAMILIES or event_type == "facilitation.move_executed"


def rework_pending(state: SessionState, events: Sequence[Event]) -> bool:
    """A fresh loop-back means rework: the target stage's engine must do
    substantive work before exit criteria may fast-forward the session again.

    "Substantive" is the whole point. Counting *any* appended record let the
    engine's own telemetry discharge the requirement — when a model call was
    refused, that refusal record alone satisfied the check and the run
    fast-forwarded on exactly the evidence the human looped back to replace,
    making the intervention a no-op.
    """
    if not state.transitions:
        return False
    last = state.transitions[-1]
    if not is_loopback(last["from"], last["to"]):
        return False
    target, since = last["to"], last["seq"]
    return not any(
        event.seq > since and event.stage == target and is_substantive_work(event.type)
        for event in events
    )


def halt_result(state: SessionState) -> RunResult | None:
    """Why the run stops here without doing anything further, in precedence
    order — or None if it may keep going."""
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
    return None


def approved_gate_target(state: SessionState) -> Stage | None:
    """The stage an approved gate clears the way to, or None.

    A gate approved for some other stage is stale — a loop-back moved the run
    since the approval — and never fires a transition.
    """
    gate = state.approved_gate
    if gate is None or gate.from_stage != state.stage:
        return None
    return gate.to_stage


def stall_detail(stage: Stage, runs: int, verdict: CriteriaVerdict, rework: bool) -> str:
    """Why a stage is being abandoned after too many engine passes."""
    if rework:
        return (
            f"engine for {stage} ran {runs} times after a loop-back without journaling "
            "any substantive work; the reason for the loop-back is still unaddressed"
        )
    return (
        f"engine for {stage} ran {runs} times without meeting the exit criteria; "
        f"unmet: {verdict.unmet}"
    )


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
            # Refuse an unreadable gate policy before anything is journaled and
            # before a single token is spent. The policy is immutable for the
            # life of the session, so resolving it once here holds for the run.
            policy = resolve_gate_policy(state)
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
            return self._loop(store, max_transitions, policy)

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

    def _loop(
        self, store: JournalStore, max_transitions: int | None, policy: GatePolicy
    ) -> RunResult:
        transitions = 0
        engine_attempts: dict[Stage, int] = {}
        while True:
            # One journal read per iteration: every decision below folds or
            # filters this same snapshot.
            events = list(store.events())
            state = replay(events)

            halt = halt_result(state)
            if halt is not None:
                return halt
            if self._budget_exhausted(state):
                return self._stop_on_budget(store, state)
            if max_transitions is not None and transitions >= max_transitions:
                return RunResult("stepped", state.stage)

            approved_to = approved_gate_target(state)
            if approved_to is not None:
                self._fire(store, state, approved_to, "gate approved")
                transitions += 1
                continue

            verdict = can_exit(state.stage, state)
            rework = rework_pending(state, events)
            if verdict.ok and not rework:
                if self._maybe_request_gate(store, state, policy):
                    continue  # loop re-reads state and halts on the pending gate
                self._fire(store, state, FORWARD[state.stage], "exit criteria met")
                transitions += 1
                continue

            engine_attempts[state.stage] = engine_attempts.get(state.stage, 0) + 1
            if engine_attempts[state.stage] > self.MAX_ENGINE_ATTEMPTS_PER_STAGE:
                raise StalledStageError(
                    stall_detail(state.stage, engine_attempts[state.stage] - 1, verdict, rework)
                )
            result = self._run_engine(store, state, verdict)
            if result is not None:
                return result

    def _budget_exhausted(self, state: SessionState) -> bool:
        total = state.config.get("budgets", {}).get("total_tokens")
        return total is not None and state.tokens_spent() >= total

    def _stop_on_budget(self, store: JournalStore, state: SessionState) -> RunResult:
        store.append(
            type="session.stopped",
            stage=state.stage,
            actor=SYSTEM_ACTOR,
            payload={"reason": "budget_exhausted", "detail": "token budget spent"},
        )
        return RunResult("stopped", state.stage, detail="budget_exhausted")

    def _maybe_request_gate(
        self, store: JournalStore, state: SessionState, policy: GatePolicy
    ) -> bool:
        if not gate_required(policy, state.stage):
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
        # Nothing appended means nothing to replay: the state this pass was
        # given is still current, so the criteria can be re-read from it.
        if store.last_seq == seq_before and not can_exit(state.stage, state).ok:
            raise StalledStageError(
                f"engine for {state.stage} made no progress; unmet: {verdict.unmet}"
            )
        return None
