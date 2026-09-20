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
    pending_question_id: str | None = None  # set when an input mailbox holds the question
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


class OpportunityCell(BaseModel):
    """One (segment, outcome) cell of the Ulwick opportunity matrix.

    `score` is the mean Ulwick opportunity score over the segment's personas who
    scored the outcome; `n` is how many did. `low_confidence` is `n < 2` — a
    single-persona cell is not a finding, and the flag travels with the number so
    a thin cell reads as thin on every surface.
    """

    segment: str
    outcome: str
    score: float
    n: int
    low_confidence: bool


class OpportunityMatrix(BaseModel):
    """Segment x outcome opportunity landscape, derived purely from the journal.

    The one shape shared by the `opportunities` verb's `--json` output and the
    report's "Underserved by segment" heatmap, so the CLI number and the report
    number agree for a given session. `segments` and `outcomes` are the ordered
    axes; `cells` carries the populated (segment, outcome) triples (a pair with no
    scoring personas has no cell). `simulated` carries the dojo framing.
    """

    kind: Literal["opportunity_matrix"] = "opportunity_matrix"
    name: str
    segments: list[str]
    outcomes: list[str]
    cells: list[OpportunityCell]
    simulated: bool = False

    def cell(self, segment: str, outcome: str) -> OpportunityCell | None:
        return next((c for c in self.cells if c.segment == segment and c.outcome == outcome), None)


class OpportunityDeltaOut(BaseModel):
    run: Literal["both", "new", "old"]
    statement: str
    confidence_class: str
    old_score: float | None = None
    new_score: float | None = None
    score_delta: float | None = None
    old_band: str | None = None
    new_band: str | None = None


class AssumptionFlipOut(BaseModel):
    run: Literal["both", "new", "old"]
    statement: str
    confidence_class: str
    old_score: str | None = None
    new_score: str | None = None


class CapabilityChangeOut(BaseModel):
    run: Literal["both", "new", "old"]
    statement: str
    confidence_class: str
    change: Literal["added", "removed", "changed"]


class VerdictChangeOut(BaseModel):
    old_verdict: str | None
    new_verdict: str | None
    changed: bool
    old_confidence_class: str
    new_confidence_class: str


class DiffResult(BaseModel):
    kind: Literal["diff"] = "diff"
    old_session: str
    new_session: str
    product: str
    opportunities: list[OpportunityDeltaOut] = Field(default_factory=list)
    assumptions: list[AssumptionFlipOut] = Field(default_factory=list)
    capabilities: list[CapabilityChangeOut] = Field(default_factory=list)
    verdict: VerdictChangeOut | None = None


def diff_result(data) -> DiffResult:
    """Build the CLI/MCP contract shape from a `diffing.DiffData` — the one
    derived structure both surfaces consume, so the table and `--json` never
    disagree. Every row keeps its run provenance and confidence class."""
    return DiffResult(
        old_session=data.old_session,
        new_session=data.new_session,
        product=data.product,
        opportunities=[OpportunityDeltaOut(**vars(o)) for o in data.opportunities],
        assumptions=[AssumptionFlipOut(**vars(a)) for a in data.assumptions],
        capabilities=[CapabilityChangeOut(**vars(c)) for c in data.capabilities],
        verdict=VerdictChangeOut(**vars(data.verdict)) if data.verdict is not None else None,
    )


class LaneBreakdown(BaseModel):
    lane: str  # exploration | research | synthesis
    calls: int
    tokens: int
    cost_usd: float


class EstimateResult(BaseModel):
    """A modeled pre-flight cost estimate: a range, a per-lane breakdown, and the
    assumptions behind it. Derived, never measured - see `caveat`."""

    kind: Literal["estimate"] = "estimate"
    panel_size: int
    provider: str
    model: str | None = None
    cost_low_usd: float
    cost_point_usd: float
    cost_high_usd: float
    total_calls: int
    total_tokens: int
    lanes: list[LaneBreakdown] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    caveat: str


def estimate_result(estimate) -> EstimateResult:
    """Map a `bokken.estimate.Estimate` onto the shared contract shape."""
    return EstimateResult(
        panel_size=estimate.panel_size,
        provider=estimate.provider,
        model=estimate.model,
        cost_low_usd=estimate.cost_low_usd,
        cost_point_usd=estimate.cost_point_usd,
        cost_high_usd=estimate.cost_high_usd,
        total_calls=estimate.total_calls,
        total_tokens=estimate.total_tokens,
        lanes=[
            LaneBreakdown(lane=la.lane, calls=la.calls, tokens=la.tokens, cost_usd=la.cost_usd)
            for la in estimate.lanes
        ],
        assumptions=list(estimate.assumptions),
        caveat=estimate.caveat,
    )


class BacklogItem(BaseModel):
    rank: int
    kind: Literal["assumption", "research_debt"]
    # impact/uncertainty/score are the assumption register fields; a
    # research-debt item leaves them None (it is an open question, not a scored
    # assumption). `priority` is the ordinal impact x uncertainty product used
    # to rank, exposed so an export can sort or filter deterministically.
    impact: str | None = None
    uncertainty: str | None = None
    score: str | None = None
    priority: int | None = None
    confidence_class: str
    source: str
    statement: str


class BacklogResult(BaseModel):
    kind: Literal["backlog"] = "backlog"
    name: str
    mode: str | None
    items: list[BacklogItem] = Field(default_factory=list)
    # Register counts over the whole assumption register (not just the backlog):
    # supported items are excluded from `items` but still counted here.
    supported: int = 0
    contradicted: int = 0
    untested: int = 0
    research_debt: int = 0
    flip_the_verdict: str = ""
    # Honesty framing: a simulated-only backlog restates the dojo banner and
    # the requires-real-validation context so it is never read as validated fact.
    dojo_banner: bool = False
    requires_real_validation: bool = False
    simulated_only: bool = False
    banner: str | None = None


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


def cost_payload(session_dir) -> dict:
    """The costs payload both surfaces emit (`bokken costs --json` and the
    `cost_report` tool): list-price rows, total, cache hit rate, the functional
    rollup, and grounding health. Lane economics are only half the picture: a
    cheaper sidekick that paraphrases shows up as backstop-forced abstentions
    in `grounding`, not as savings. Lazy imports keep the dossier/report stack
    off the CLI startup path."""
    from bokken.dossier.model import build_model
    from bokken.panel import grounding_health
    from bokken.report.context import cost_rows, functional_rollup

    rows = cost_rows(build_model(session_dir))
    hit = sum(r["cache_read"] for r in rows)
    raw = sum(r["input"] for r in rows)
    return {
        "rows": rows,
        "total_usd": round(sum(r["cost_usd"] for r in rows), 2),
        "cache_hit_rate": round(hit / (hit + raw), 3) if hit + raw else 0.0,
        "rollup": functional_rollup(rows),
        "grounding": grounding_health(read_events(session_dir)),
    }
