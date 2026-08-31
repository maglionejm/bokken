"""Replay: fold a journal into derived session state. Pure — no I/O inside the fold."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bokken.journal.schema import Event, Mode, Stage, StopReason
from bokken.journal.store import read_events

OptionStatus = str  # "alive" | "parked" | "killed" | "merged" | "split"


@dataclass
class PendingGate:
    gate_id: str
    from_stage: Stage
    to_stage: Stage
    requested_by: str


@dataclass
class EvidenceItem:
    id: str
    stage: Stage | None
    source: str
    confidence_class: str
    speaker: str | None
    segment: str | None = None


@dataclass
class ResearchDebtItem:
    id: str
    stage: Stage | None
    question: str
    gap: str
    segment: str | None = None


@dataclass
class Insight:
    id: str
    kind: str
    statement: str
    refs: list[str]
    ungrounded: bool


@dataclass
class OptionNode:
    id: str
    summary: str
    contributor: str
    origin: str  # created | built_on | merged | split
    parents: list[str]
    status: OptionStatus = "alive"
    status_reason: str | None = None


@dataclass
class Decision:
    id: str
    stage: Stage | None
    question: str
    resolution: str
    options: list[str]
    dissent: list[dict[str, Any]]
    requires_real_validation: bool


@dataclass
class Assumption:
    id: str
    statement: str
    impact: str
    uncertainty: str
    score: str | None = None
    score_refs: list[str] = field(default_factory=list)


@dataclass
class ArtifactRef:
    id: str
    path: str
    kind: str
    content_hash: str
    refs: list[str]


@dataclass
class SessionState:
    session_id: str = ""
    name: str = ""
    mode: Mode | None = None
    brief: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    stage: Stage = "intake"
    pending_gate: PendingGate | None = None
    approved_gate: PendingGate | None = None
    stopped: StopReason | None = None
    evidence: dict[str, EvidenceItem] = field(default_factory=dict)
    research_debt: list[ResearchDebtItem] = field(default_factory=list)
    insights: dict[str, Insight] = field(default_factory=dict)
    options: dict[str, OptionNode] = field(default_factory=dict)
    decisions: dict[str, Decision] = field(default_factory=dict)
    assumptions: dict[str, Assumption] = field(default_factory=dict)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    moves_executed: dict[str, int] = field(default_factory=dict)
    moves_by_stage: dict[str, dict[str, int]] = field(default_factory=dict)
    moves_suppressed: list[dict[str, str]] = field(default_factory=list)
    token_usage: dict[str, dict[str, int]] = field(default_factory=dict)
    transitions: list[dict[str, Any]] = field(default_factory=list)
    events_since_transition: int = 0  # substantive (non-session.*) events
    last_seq: int = 0
    last_ts: datetime | None = None

    @property
    def evidence_by_class(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.evidence.values():
            counts[item.confidence_class] = counts.get(item.confidence_class, 0) + 1
        return counts

    def tokens_spent(self, routing_class: str | None = None) -> int:
        classes = [routing_class] if routing_class else list(self.token_usage)
        return sum(
            self.token_usage.get(c, {}).get("input_tokens", 0)
            + self.token_usage.get(c, {}).get("output_tokens", 0)
            for c in classes
        )


def replay(events: Iterable[Event]) -> SessionState:
    """Fold events (in seq order) into SessionState. Deterministic and pure."""
    state = SessionState()
    for event in events:
        _apply(state, event)
    return state


def replay_session(session_dir: Path) -> SessionState:
    return replay(read_events(session_dir))


def _apply(state: SessionState, event: Event) -> None:
    p = event.payload
    state.last_seq = event.seq
    state.last_ts = event.ts
    state.session_id = event.session_id
    if event.type == "transition.fired":
        state.events_since_transition = 0
    elif not event.type.startswith("session."):
        state.events_since_transition += 1

    if event.type == "session.created":
        state.name = p["name"]
        state.mode = p["mode"]
        state.brief = p["brief"]
        state.config = p.get("config", {})
    elif event.type == "session.resumed":
        state.stopped = None
        overrides = p.get("config_overrides")
        if isinstance(overrides, dict):
            for key, value in overrides.items():
                if isinstance(value, dict) and isinstance(state.config.get(key), dict):
                    state.config[key] = {**state.config[key], **value}
                else:
                    state.config[key] = value
    elif event.type == "session.gate_requested":
        state.pending_gate = PendingGate(
            gate_id=p["gate_id"],
            from_stage=p["from_stage"],
            to_stage=p["to_stage"],
            requested_by=event.actor.name,
        )
    elif event.type == "session.gate_resolved":
        if state.pending_gate and state.pending_gate.gate_id == p["gate_id"]:
            if p["resolution"] == "approve":
                state.approved_gate = state.pending_gate
            state.pending_gate = None
    elif event.type == "session.stopped":
        state.stopped = p["reason"]
    elif event.type == "evidence.captured":
        state.evidence[event.id] = EvidenceItem(
            id=event.id,
            stage=event.stage,
            source=p["source"],
            confidence_class=p["confidence_class"],
            speaker=p.get("speaker"),
            segment=p.get("segment"),
        )
    elif event.type == "evidence.abstained":
        state.research_debt.append(
            ResearchDebtItem(
                id=event.id,
                stage=event.stage,
                question=p["question"],
                gap=p["gap"],
                segment=p.get("segment"),
            )
        )
    elif event.type == "interpretation.derived":
        state.insights[event.id] = Insight(
            id=event.id,
            kind=p["kind"],
            statement=p["statement"],
            refs=list(event.refs),
            ungrounded=p["ungrounded"],
        )
    elif event.type in ("option.created", "option.built_on", "option.merged", "option.split"):
        origin = event.type.split(".", 1)[1]
        state.options[event.id] = OptionNode(
            id=event.id,
            summary=p["summary"],
            contributor=event.actor.name,
            origin=origin,
            parents=list(event.refs),
        )
        if event.type == "option.merged":
            for ref in event.refs:
                node = state.options.get(ref)
                if node and node.status == "alive":
                    node.status = "merged"
    elif event.type in ("option.parked", "option.killed"):
        status = "parked" if event.type == "option.parked" else "killed"
        for ref in event.refs:
            node = state.options.get(ref)
            if node:
                node.status = status
                node.status_reason = p["reason"]
    elif event.type == "decision.recorded":
        state.decisions[event.id] = Decision(
            id=event.id,
            stage=event.stage,
            question=p["question"],
            resolution=p["resolution"],
            options=list(p["options"]),
            dissent=list(p["dissent"]),
            requires_real_validation=p["requires_real_validation"],
        )
    elif event.type == "assumption.registered":
        state.assumptions[event.id] = Assumption(
            id=event.id,
            statement=p["statement"],
            impact=p["impact"],
            uncertainty=p["uncertainty"],
        )
    elif event.type == "assumption.scored":
        for ref in event.refs:
            assumption = state.assumptions.get(ref)
            if assumption:
                assumption.score = p["score"]
                assumption.score_refs = [r for r in event.refs if r != ref]
    elif event.type == "facilitation.move_executed":
        move_id = p["move_id"]
        state.moves_executed[move_id] = state.moves_executed.get(move_id, 0) + 1
        if event.stage is not None:
            by_stage = state.moves_by_stage.setdefault(event.stage, {})
            by_stage[move_id] = by_stage.get(move_id, 0) + 1
    elif event.type == "facilitation.move_suppressed":
        state.moves_suppressed.append({"move_id": p["move_id"], "reason": p["reason"]})
    elif event.type == "transition.fired":
        state.stage = p["to_stage"]
        state.approved_gate = None
        state.transitions.append(
            {
                "from": p["from_stage"],
                "to": p["to_stage"],
                "condition": p["condition"],
                "refs": list(event.refs),
                "seq": event.seq,
            }
        )
    elif event.type == "model.called":
        usage = p.get("usage", {})
        bucket = state.token_usage.setdefault(
            p["routing_class"],
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        )
        for key in bucket:
            bucket[key] += int(usage.get(key, 0) or 0)
    elif event.type == "artifact.generated":
        state.artifacts.append(
            ArtifactRef(
                id=event.id,
                path=p["path"],
                kind=p["kind"],
                content_hash=p["content_hash"],
                refs=list(event.refs),
            )
        )
