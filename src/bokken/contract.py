"""Shared result shapes: one contract for the CLI's --json output and MCP tool results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from bokken.journal import SessionState, replay
from bokken.journal.store import read_events
from bokken.journal.workspace import SessionInfo


class PendingGateOut(BaseModel):
    gate_id: str
    from_stage: str
    to_stage: str
    resolve_hint: str


class StatusResult(BaseModel):
    kind: Literal["status"] = "status"
    name: str
    mode: str | None
    stage: str
    state: Literal["complete", "gate_pending", "stopped", "in_progress"]
    pending_gate: PendingGateOut | None = None
    stopped_reason: str | None = None
    evidence_by_class: dict[str, int] = Field(default_factory=dict)
    research_debt: int = 0
    options_alive: int = 0
    assumptions_scored: str = "0/0"
    tokens_spent: int = 0
    last_seq: int = 0
    last_ts: datetime | None = None


class RunOutcome(BaseModel):
    kind: Literal["run"] = "run"
    halt: str
    stage: str
    detail: str = ""
    pending_question: str | None = None
    finalization: str | None = None  # set when a completed run generated dossier/handoff
    cost_usd: float | None = None  # session-to-date list price from journaled calls
    model_calls: int | None = None


class HandoffResult(BaseModel):
    kind: Literal["handoff"] = "handoff"
    package_dir: str
    change_id: str
    capabilities: list[str]
    adapters: list[str] = []  # emitted target-specific execution files


class SessionListItem(BaseModel):
    name: str
    slug: str
    stage: str
    mode: str | None
    last_ts: datetime | None


class SessionList(BaseModel):
    kind: Literal["sessions"] = "sessions"
    sessions: list[SessionListItem]


class GateResult(BaseModel):
    kind: Literal["gate"] = "gate"
    resolution: str
    stage: str


class LoopbackResult(BaseModel):
    kind: Literal["loopback"] = "loopback"
    to_stage: str
    stage: str


class DossierResult(BaseModel):
    kind: Literal["dossier"] = "dossier"
    markdown_path: str
    json_path: str
    status: Literal["complete", "partial"]


class ExportResult(BaseModel):
    kind: Literal["export"] = "export"
    pptx_path: str
    html_path: str


def status_of(name: str, state: SessionState) -> StatusResult:
    if state.stage == "complete":
        overall = "complete"
    elif state.pending_gate is not None:
        overall = "gate_pending"
    elif state.stopped is not None:
        overall = "stopped"
    else:
        overall = "in_progress"
    gate = None
    if state.pending_gate is not None:
        gate = PendingGateOut(
            gate_id=state.pending_gate.gate_id,
            from_stage=state.pending_gate.from_stage,
            to_stage=state.pending_gate.to_stage,
            resolve_hint=f"bokken gate {name} approve|reject --reason <text>",
        )
    scored = sum(1 for a in state.assumptions.values() if a.score is not None)
    return StatusResult(
        name=name,
        mode=state.mode,
        stage=state.stage,
        state=overall,  # type: ignore[arg-type]
        pending_gate=gate,
        stopped_reason=state.stopped,
        evidence_by_class=state.evidence_by_class,
        research_debt=len(state.research_debt),
        options_alive=sum(1 for o in state.options.values() if o.status == "alive"),
        assumptions_scored=f"{scored}/{len(state.assumptions)}",
        tokens_spent=state.tokens_spent(),
        last_seq=state.last_seq,
        last_ts=state.last_ts,
    )


def status_for_dir(name: str, session_dir) -> StatusResult:
    return status_of(name, replay(read_events(session_dir)))


def list_result(infos: list[SessionInfo]) -> SessionList:
    return SessionList(
        sessions=[
            SessionListItem(name=i.name, slug=i.slug, stage=i.stage, mode=i.mode, last_ts=i.last_ts)
            for i in infos
        ]
    )
