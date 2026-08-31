"""Journal event schema v1: envelope, taxonomy, payloads, canonical hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1"
GENESIS_HASH = "0" * 64

Stage = Literal["intake", "empathize", "define", "ideate", "prototype", "test", "complete"]
STAGES: tuple[Stage, ...] = (
    "intake",
    "empathize",
    "define",
    "ideate",
    "prototype",
    "test",
    "complete",
)

ConfidenceClass = Literal["observed", "reported", "assumed", "simulated"]
ActorKind = Literal["human", "agent", "system"]
Mode = Literal["founder", "dojo"]
StopReason = Literal[
    "completed", "budget_exhausted", "novelty_floor", "criteria_met", "human_stop", "error"
]
RoutingClass = Literal["cognition", "extraction", "generation"]
SuppressionReason = Literal["budget_exhausted", "out_of_stage", "mode_config", "superseded"]


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ActorKind
    name: str
    model: str | None = None
    persona_id: str | None = None


# --- Payload models (extra="allow": tolerant reader, forward compatible) ---


class Payload(BaseModel):
    model_config = ConfigDict(extra="allow")


class BriefInputs(Payload):
    """Tangible inputs a run starts from: an app repo to explore, business and
    performance metrics, and human discussions/interviews/needs statements."""

    repo: str | None = None
    metrics: list[str] = Field(default_factory=list)
    discussions: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


class Brief(Payload):
    problem_space: str
    constraints: list[str] = Field(default_factory=list)
    target_segments: list[str]
    success_criteria: list[str]
    risk_tolerance: str
    inputs: BriefInputs = Field(default_factory=BriefInputs)


class SessionCreated(Payload):
    name: str
    mode: Mode
    brief: Brief
    config: dict[str, Any] = Field(default_factory=dict)


class SessionResumed(Payload):
    pass


class SessionGateRequested(Payload):
    gate_id: str
    from_stage: Stage
    to_stage: Stage


class SessionGateResolved(Payload):
    gate_id: str
    resolution: Literal["approve", "reject"]
    reason: str | None = None

    @model_validator(mode="after")
    def _reject_needs_reason(self) -> SessionGateResolved:
        if self.resolution == "reject" and not self.reason:
            raise ValueError("gate rejection requires a reason")
        return self


class SessionStopped(Payload):
    reason: StopReason
    detail: str | None = None


class EvidenceCaptured(Payload):
    content: str
    source: str
    confidence_class: ConfidenceClass
    speaker: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)


class EvidenceAbstained(Payload):
    question: str
    gap: str


class InterpretationDerived(Payload):
    kind: Literal["insight", "theme", "pov", "hmw"]
    statement: str
    ungrounded: bool = False


class OptionCreated(Payload):
    summary: str


class OptionBuiltOn(Payload):
    summary: str


class OptionMerged(Payload):
    summary: str
    reason: str | None = None


class OptionSplit(Payload):
    summary: str
    reason: str | None = None


class OptionParked(Payload):
    reason: str


class OptionKilled(Payload):
    reason: str


class DecisionPosition(Payload):
    actor: str
    position: str


class DecisionDissent(Payload):
    actor: str
    reservation: str


class DecisionRecorded(Payload):
    question: str
    options: list[str]
    criteria: list[str]
    positions: list[DecisionPosition] = Field(default_factory=list)
    resolution: str
    dissent: list[DecisionDissent] = Field(default_factory=list)
    requires_real_validation: bool = False


class AssumptionRegistered(Payload):
    statement: str
    impact: Literal["low", "medium", "high"]
    uncertainty: Literal["low", "medium", "high"]


class AssumptionScored(Payload):
    score: Literal["supported", "contradicted", "untested"]
    rationale: str | None = None


class MoveExecuted(Payload):
    move_id: str
    trigger: str
    params: dict[str, Any] = Field(default_factory=dict)
    outcome: str | None = None


class MoveSuppressed(Payload):
    move_id: str
    trigger: str
    reason: SuppressionReason


class TransitionFired(Payload):
    from_stage: Stage
    to_stage: Stage
    condition: str


class TokenUsage(Payload):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


class ModelCalled(Payload):
    routing_class: RoutingClass
    model: str
    prompt_id: str
    prompt_version: str
    prompt_hash: str
    request_id: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    status: Literal["ok", "refused", "error", "truncated"]
    duration_ms: int | None = None


class ArtifactGenerated(Payload):
    path: str
    kind: str
    content_hash: str


TAXONOMY: dict[str, type[Payload]] = {
    "session.created": SessionCreated,
    "session.resumed": SessionResumed,
    "session.gate_requested": SessionGateRequested,
    "session.gate_resolved": SessionGateResolved,
    "session.stopped": SessionStopped,
    "evidence.captured": EvidenceCaptured,
    "evidence.abstained": EvidenceAbstained,
    "interpretation.derived": InterpretationDerived,
    "option.created": OptionCreated,
    "option.built_on": OptionBuiltOn,
    "option.merged": OptionMerged,
    "option.split": OptionSplit,
    "option.parked": OptionParked,
    "option.killed": OptionKilled,
    "decision.recorded": DecisionRecorded,
    "assumption.registered": AssumptionRegistered,
    "assumption.scored": AssumptionScored,
    "facilitation.move_executed": MoveExecuted,
    "facilitation.move_suppressed": MoveSuppressed,
    "transition.fired": TransitionFired,
    "model.called": ModelCalled,
    "artifact.generated": ArtifactGenerated,
}

# Event types that must reference prior events to be meaningful.
_REFS_REQUIRED = {"option.built_on", "option.merged", "option.killed", "assumption.scored"}


class Event(BaseModel):
    """A persisted journal record (envelope + validated payload)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    seq: int = Field(ge=1)
    id: str
    ts: datetime
    session_id: str
    type: str
    stage: Stage | None
    actor: Actor
    payload: dict[str, Any]
    refs: list[str] = Field(default_factory=list)
    prev_hash: str
    hash: str = ""

    @field_validator("ts")
    @classmethod
    def _ts_must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() != UTC.utcoffset(None):
            raise ValueError("ts must be an aware UTC timestamp")
        return v

    @field_validator("type")
    @classmethod
    def _type_in_taxonomy(cls, v: str) -> str:
        if v not in TAXONOMY:
            raise ValueError(f"unknown event type: {v}")
        return v

    @model_validator(mode="after")
    def _validate_payload_and_invariants(self) -> Event:
        model = TAXONOMY[self.type]
        parsed = model.model_validate(self.payload)
        # Normalize known fields while preserving unknown (forward-compat) fields.
        self.payload = {**self.payload, **parsed.model_dump(exclude_unset=False)}
        if self.type in _REFS_REQUIRED and not self.refs:
            raise ValueError(f"{self.type} requires non-empty refs")
        if self.type == "evidence.captured":
            if (
                self.actor.persona_id is not None
                and self.payload["confidence_class"] != "simulated"
            ):
                raise ValueError("persona evidence must have confidence_class 'simulated'")
            if self.actor.kind == "human" and self.payload["confidence_class"] == "simulated":
                raise ValueError("human evidence cannot be 'simulated'")
        if (
            self.type == "interpretation.derived"
            and not self.refs
            and not self.payload["ungrounded"]
        ):
            raise ValueError("interpretation without refs must set ungrounded=true")
        return self


def canonical_bytes(event: Event) -> bytes:
    """Canonical serialization of a record excluding its own hash."""
    data = event.model_dump(mode="json", exclude={"hash"})
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def compute_hash(event: Event) -> str:
    return hashlib.sha256(canonical_bytes(event)).hexdigest()


def seal(event: Event) -> Event:
    """Return the event with its hash computed over the canonical form."""
    return event.model_copy(update={"hash": compute_hash(event)})


def new_event(
    *,
    seq: int,
    session_id: str,
    type: str,
    stage: Stage | None,
    actor: Actor,
    payload: dict[str, Any] | Payload,
    refs: list[str] | None = None,
    prev_hash: str,
    ts: datetime | None = None,
) -> Event:
    """Build and seal a record; validation errors raise before anything is written."""
    if isinstance(payload, Payload):
        payload = payload.model_dump()
    event = Event(
        seq=seq,
        id=uuid4().hex,
        ts=ts or datetime.now(UTC),
        session_id=session_id,
        type=type,
        stage=stage,
        actor=actor,
        payload=payload,
        refs=refs or [],
        prev_hash=prev_hash,
    )
    return seal(event)


def parse_line(line: str) -> Event:
    """Parse one persisted JSONL line back into an Event (tolerant on payload extras)."""
    return Event.model_validate_json(line)
