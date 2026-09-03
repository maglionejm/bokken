"""Journal event schema v1: envelope, taxonomy, payloads, canonical hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal, TypeVar, cast
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
    model_validator,
)

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
RoutingClass = Literal["research", "challenge", "cognition", "extraction", "generation", "sidekick"]
SuppressionReason = Literal["budget_exhausted", "out_of_stage", "mode_config", "superseded"]
ConsentOutcome = Literal["granted", "declined", "no_response", "ambiguous"]


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ActorKind
    name: str
    model: str | None = None
    persona_id: str | None = None


# --- Payload models (extra="allow": tolerant reader, forward compatible) ---
#
# `extra="allow"` is a reader guarantee, not a writer license: a key a newer
# Bokken wrote must survive this version's read untouched. The write path is
# strict instead (see `EXTENSION_KEYS` and `Event._validate_payload_and_invariants`),
# because the Journal is append-only and a key misspelled on append is immortal.


class Payload(BaseModel):
    model_config = ConfigDict(extra="allow")


PayloadT = TypeVar("PayloadT", bound=Payload)


class BriefInputs(Payload):
    """Tangible inputs a run starts from: an app repo to explore, business and
    performance metrics, and human discussions/interviews/needs statements."""

    repo: str | None = None
    app_url: str | None = None
    metrics: list[str] = Field(default_factory=list)
    discussions: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


class Brief(Payload):
    problem_space: str
    allow_web_research: bool = False
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


class EvidenceInputRejected(Payload):
    """A declared corpus input that never entered the record, and why."""

    path: str
    reason: str


class InterpretationDerived(Payload):
    kind: Literal[
        "insight", "theme", "pov", "hmw", "desired_outcome", "outcome_score", "opportunity"
    ]
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
    status: Literal["ok", "refused", "error", "truncated", "budget_exhausted"]
    duration_ms: int | None = None


class InterviewConsentRequested(Payload):
    """An outbound contact asking a real human to take part, before it happens."""

    participant: str
    channel: str


class InterviewConsentResolved(Payload):
    """What came back. Only `granted` may be followed by an interview question."""

    participant: str
    channel: str
    outcome: ConsentOutcome
    basis: str


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
    "evidence.input_rejected": EvidenceInputRejected,
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
    "interview.consent_requested": InterviewConsentRequested,
    "interview.consent_resolved": InterviewConsentResolved,
    "artifact.generated": ArtifactGenerated,
}

# Payload keys that producers write today but that are deliberately NOT fields of
# their payload model. They are declared here so the strict write path can tell a
# known extension from a typo, without changing a single byte on disk.
#
# Why not promote them to typed fields? Because the payload normalization below
# materializes every declared default into the stored payload, and `verify_chain`
# recomputes each record's hash from the validated payload. Adding a defaulted
# field to an existing payload model therefore injects that default when an older
# record is re-read, changing its hash and breaking the chain of every journal
# written before the promotion — a session that can no longer even be opened.
# Promotion is a schema-versioning change of its own; this registry is what makes
# the write path honest in the meantime. Keys here still read back through
# `Event.payload` (and `typed_payload.model_extra`), never through attributes.
EXTENSION_KEYS: dict[str, frozenset[str]] = {
    "session.resumed": frozenset({"config_overrides"}),
    # `segment` carries the target segment a turn belongs to; the empathize exit
    # gate reads it to prove every declared segment was heard or logged as debt.
    # `grounding` records whether a persona answer came from the corpus or the
    # profile. `participant`/`question` come from real remote interviews, `url`
    # from web-research findings.
    "evidence.captured": frozenset({"segment", "grounding", "participant", "question", "url"}),
    "evidence.abstained": frozenset({"segment"}),
    # Ulwick opportunity bookkeeping: per-outcome scores, bands and job steps.
    "interpretation.derived": frozenset(
        {"job_step", "importance", "satisfaction", "persona_id", "score", "band", "per_persona"}
    ),
    # A private thought attached to an idea, kept out of the shared pool.
    "option.created": frozenset({"private_thought", "visibility"}),
    "decision.recorded": frozenset({"confidence", "pivoted_by_timebox"}),
    # `requested_model` is fallback provenance: what was asked for versus served.
    "model.called": frozenset({"requested_model", "web_search"}),
    # Per-kind artifact detail: panel rosters, handoff specs, UI runs.
    "artifact.generated": frozenset(
        {
            "panel_kind",
            "persona_ids",
            "seed",
            "change_id",
            "capabilities",
            "feature",
            "url",
            "viewport",
        }
    ),
}

# Passed as the Pydantic validation context by `parse_line`: reads of persisted
# records tolerate undeclared payload keys, writes do not.
TOLERANT_READ: dict[str, bool] = {"tolerate_undeclared_payload_keys": True}


def _tolerates_undeclared(context: Any) -> bool:
    return isinstance(context, dict) and bool(context.get("tolerate_undeclared_payload_keys"))


def _undeclared_keys(payload: Payload, prefix: str = "") -> list[str]:
    """Dotted paths of keys no payload model declares, nested models included."""
    found = [f"{prefix}{key}" for key in sorted(payload.model_extra or {})]
    for name, value in payload:
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, Payload):
                found.extend(_undeclared_keys(item, f"{prefix}{name}."))
    return found


# Event types that must reference prior events to be meaningful.
_REFS_REQUIRED = {
    "option.built_on",
    "option.merged",
    "option.killed",
    "assumption.scored",
    "interview.consent_resolved",
}


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

    # The taxonomy model parsed during validation, kept so the typed read path
    # costs nothing extra. Private: never dumped, so it cannot affect the hash.
    _typed_payload: Payload | None = PrivateAttr(default=None)

    @property
    def typed_payload(self) -> Payload:
        """This record's payload as its `TAXONOMY` model: the typed read path.

        Readers get attribute access, static types and rename safety over the one
        file format the whole system is built on, instead of indexing a dict by
        string key. Forward compatibility is preserved in both directions: a key
        this version does not declare is kept verbatim in `model_extra` here and
        in `Event.payload`, so nothing is dropped by a read-modify-write cycle.

        A caller that genuinely needs the raw mapping — generic tooling, or one of
        the extension keys in `EXTENSION_KEYS` — keeps reading `Event.payload`,
        which this accessor never touches.
        """
        if self._typed_payload is None:
            self._typed_payload = TAXONOMY[self.type].model_validate(self.payload)
        return self._typed_payload

    def payload_as(self, model: type[PayloadT]) -> PayloadT:
        """`typed_payload` narrowed to `model`, for static typing at the call site.

        Raises `TypeError` when this event type does not map to `model`, so a
        reader that dispatched on `event.type` and then asked for the wrong
        payload class fails loudly instead of quietly reading `None`s.
        """
        declared = TAXONOMY[self.type]
        if not issubclass(declared, model):
            raise TypeError(
                f"{self.type} carries a {declared.__name__} payload, not {model.__name__}"
            )
        return cast(PayloadT, self.typed_payload)

    def extension(self, key: str) -> Any:
        """Read one declared-but-untyped extension key (see `EXTENSION_KEYS`).

        Extension keys have no attribute to autocomplete, so this is the checked
        way to read one: an undeclared name raises instead of returning `None`
        and letting a misspelling become a quietly missing value.
        """
        if key not in EXTENSION_KEYS.get(self.type, frozenset()):
            raise KeyError(f"{key!r} is not a declared extension key of {self.type}")
        return self.payload.get(key)

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
    def _validate_payload_and_invariants(self, info: ValidationInfo) -> Event:
        model = TAXONOMY[self.type]
        parsed = model.model_validate(self.payload)
        # Strict on append, tolerant on read. `parse_line` passes TOLERANT_READ so
        # a persisted record always loads — including one written by a newer
        # Bokken, and one that already carries a typo made before this check
        # existed. Every other construction is a write, and a write that carries
        # a key nobody declared is rejected before the record can be appended:
        # the Journal is append-only, so the alternative is a permanent typo.
        if not _tolerates_undeclared(info.context):
            undeclared = [
                key
                for key in _undeclared_keys(parsed)
                if key not in EXTENSION_KEYS.get(self.type, frozenset())
            ]
            if undeclared:
                raise ValueError(
                    f"{self.type} payload carries undeclared key(s): {', '.join(undeclared)}. "
                    "Fix the spelling, add the field to the payload model, or declare it in "
                    "EXTENSION_KEYS if it is a deliberate untyped extension."
                )
        # Normalize known fields while preserving unknown (forward-compat) fields.
        # This materializes declared defaults into the stored payload, which is why
        # EXTENSION_KEYS exists rather than new model fields: see its comment.
        self.payload = {**self.payload, **parsed.model_dump(exclude_unset=False)}
        self._typed_payload = parsed
        if self.type in _REFS_REQUIRED and not self.refs:
            raise ValueError(f"{self.type} requires non-empty refs")
        # The honesty invariants read the typed payload, not the dict: a rename in
        # the payload model can no longer leave them silently unenforced.
        if isinstance(parsed, EvidenceCaptured):
            if self.actor.persona_id is not None and parsed.confidence_class != "simulated":
                raise ValueError("persona evidence must have confidence_class 'simulated'")
            if self.actor.kind == "human" and parsed.confidence_class == "simulated":
                raise ValueError("human evidence cannot be 'simulated'")
        if isinstance(parsed, InterpretationDerived) and not self.refs and not parsed.ungrounded:
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
    """Parse one persisted JSONL line back into an Event (tolerant on payload extras).

    Every read of a persisted record goes through here, and reads never reject:
    an already-written record is a fact, whether it came from a newer Bokken that
    declares more keys or from an older one that misspelled some. Only the write
    path is strict, so the tolerance can never be used to create a new typo.
    """
    return Event.model_validate_json(line, context=TOLERANT_READ)


def short_id(material: str) -> str:
    """Stable 12-hex identifier for derived entities (personas, sources, questions)."""
    import hashlib

    return hashlib.sha256(material.encode()).hexdigest()[:12]


def content_hash(content: str | bytes) -> str:
    """Full SHA-256 hex digest used for every journaled artifact."""
    import hashlib

    data = content.encode() if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()
