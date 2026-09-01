"""DossierModel: a typed intermediate built from the journal alone.

Both renderers consume this model, so markdown and JSON never diverge, and
honesty labels are carried on the nodes — not added (or removable) by templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from bokken.journal import read_events, replay
from bokken.orchestrator import is_loopback

DOSSIER_SCHEMA_VERSION = "1"


class EvidenceNode(BaseModel):
    id: str
    stage: str | None
    source: str
    agent: str | None = None  # journaled actor name when not a persona utterance
    confidence_class: str
    synthetic: bool
    speaker: str | None = None
    segment: str | None = None
    content: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)


class InsightNode(BaseModel):
    id: str
    kind: str
    statement: str
    evidence_ids: list[str]
    ungrounded: bool
    synthetic: bool  # grounded only in simulated/assumed evidence


class OptionNodeModel(BaseModel):
    id: str
    summary: str
    contributor: str
    origin: str
    parents: list[str]
    status: str
    status_reason: str | None = None


class DecisionNode(BaseModel):
    id: str
    stage: str | None
    question: str
    options: list[str]
    criteria: list[str]
    positions: list[dict[str, Any]]
    resolution: str
    dissent: list[dict[str, Any]]
    requires_real_validation: bool
    actor: str


class AssumptionNode(BaseModel):
    id: str
    statement: str
    impact: str
    uncertainty: str
    score: str | None


class ArtifactNode(BaseModel):
    id: str
    path: str
    kind: str
    content_hash: str
    assumption_ids: list[str]


class PersonaCard(BaseModel):
    persona_id: str
    name: str
    role: str
    segment: str | None
    panel_kind: str
    profile: dict[str, Any] = Field(default_factory=dict)


class AbstentionNode(BaseModel):
    id: str
    stage: str | None
    question: str
    gap: str


class ModelTrace(BaseModel):
    id: str
    stage: str | None
    routing_class: str
    model: str
    prompt_id: str
    prompt_version: str
    request_id: str | None
    usage: dict[str, int] = Field(default_factory=dict)
    status: str


class TransitionNode(BaseModel):
    seq: int
    from_stage: str
    to_stage: str
    condition: str
    refs: list[str]
    loopback: bool


class MoveNode(BaseModel):
    id: str
    stage: str | None
    move_id: str
    executed: bool
    trigger: str
    outcome: str | None = None
    reason: str | None = None


class PivotalMoment(BaseModel):
    kind: Literal[
        "loopback", "killed_frontrunner", "adopted_with_dissent", "gate_rejected", "timebox_pivot"
    ]
    description: str
    refs: list[str] = Field(default_factory=list)


class NegativeSpace(BaseModel):
    research_debt: list[AbstentionNode]
    suppressed_moves: list[MoveNode]
    stages_not_reached: list[str]
    gates_rejected: list[str]


class DossierModel(BaseModel):
    dossier_schema_version: str = DOSSIER_SCHEMA_VERSION
    session_id: str
    name: str
    mode: str
    status: Literal["complete", "partial"]
    stage: str
    dojo_banner: bool
    brief: dict[str, Any]
    problem_statement: DecisionNode | None
    concept: DecisionNode | None
    recommendation: DecisionNode | None
    evidence: dict[str, EvidenceNode]
    insights: dict[str, InsightNode]
    options: dict[str, OptionNodeModel]
    decisions: dict[str, DecisionNode]
    assumptions: dict[str, AssumptionNode]
    artifacts: list[ArtifactNode]
    personas: list[PersonaCard]
    abstentions: list[AbstentionNode]
    model_traces: list[ModelTrace]
    transitions: list[TransitionNode]
    moves: list[MoveNode]
    pivotal_moments: list[PivotalMoment]
    negative_space: NegativeSpace
    token_usage: dict[str, dict[str, int]]

    def resolves(self, ref: str) -> bool:
        return (
            ref in self.evidence
            or ref in self.insights
            or ref in self.options
            or ref in self.decisions
            or ref in self.assumptions
            or any(a.id == ref for a in self.artifacts)
            or any(m.id == ref for m in self.model_traces)
            or any(m.id == ref for m in self.moves)
            or any(a.id == ref for a in self.abstentions)
        )


_STAGE_ORDER = ["intake", "empathize", "define", "ideate", "prototype", "test", "complete"]


def build_model(session_dir: Path) -> DossierModel:
    events = list(read_events(session_dir))
    state = replay(events)

    evidence: dict[str, EvidenceNode] = {}
    insights: dict[str, InsightNode] = {}
    decisions: dict[str, DecisionNode] = {}
    moves: list[MoveNode] = []
    personas: list[PersonaCard] = []
    model_traces: list[ModelTrace] = []
    abstentions: list[AbstentionNode] = []
    transitions: list[TransitionNode] = []
    gates_rejected: list[str] = []

    for event in events:
        p = event.payload
        if event.type == "evidence.captured":
            evidence[event.id] = EvidenceNode(
                id=event.id,
                stage=event.stage,
                source=p["source"],
                agent=None if p.get("speaker") else event.actor.name,
                confidence_class=p["confidence_class"],
                synthetic=p["confidence_class"] == "simulated",
                speaker=p.get("speaker"),
                segment=p.get("segment"),
                content=p["content"],
                citations=p.get("citations", []),
            )
        elif event.type == "evidence.abstained":
            abstentions.append(
                AbstentionNode(id=event.id, stage=event.stage, question=p["question"], gap=p["gap"])
            )
        elif event.type == "interpretation.derived":
            grounded = [r for r in event.refs if r in evidence]
            synthetic = bool(grounded) and all(
                evidence[r].confidence_class in ("simulated", "assumed") for r in grounded
            )
            insights[event.id] = InsightNode(
                id=event.id,
                kind=p["kind"],
                statement=p["statement"],
                evidence_ids=list(event.refs),
                ungrounded=p["ungrounded"],
                synthetic=synthetic or p["ungrounded"],
            )
        elif event.type == "decision.recorded":
            decisions[event.id] = DecisionNode(
                id=event.id,
                stage=event.stage,
                question=p["question"],
                options=list(p["options"]),
                criteria=list(p["criteria"]),
                positions=list(p.get("positions", [])),
                resolution=p["resolution"],
                dissent=list(p["dissent"]),
                requires_real_validation=bool(p.get("requires_real_validation", False)),
                actor=event.actor.name,
            )
        elif event.type in ("facilitation.move_executed", "facilitation.move_suppressed"):
            executed = event.type.endswith("executed")
            moves.append(
                MoveNode(
                    id=event.id,
                    stage=event.stage,
                    move_id=p["move_id"],
                    executed=executed,
                    trigger=p["trigger"],
                    outcome=p.get("outcome") if executed else None,
                    reason=None if executed else p["reason"],
                )
            )
        elif event.type == "model.called":
            model_traces.append(
                ModelTrace(
                    id=event.id,
                    stage=event.stage,
                    routing_class=p["routing_class"],
                    model=p["model"],
                    prompt_id=p["prompt_id"],
                    prompt_version=p["prompt_version"],
                    request_id=p.get("request_id"),
                    usage=p.get("usage", {}),
                    status=p["status"],
                )
            )
        elif event.type == "transition.fired":
            transitions.append(
                TransitionNode(
                    seq=event.seq,
                    from_stage=p["from_stage"],
                    to_stage=p["to_stage"],
                    condition=p["condition"],
                    refs=list(event.refs),
                    loopback=is_loopback(p["from_stage"], p["to_stage"]),
                )
            )
        elif event.type == "session.gate_resolved" and p["resolution"] == "reject":
            gates_rejected.append(p.get("reason") or p["gate_id"])
        elif event.type == "artifact.generated" and p.get("kind") == "panel_manifest":
            manifest_path = session_dir / p["path"]
            if manifest_path.exists():
                import json as _json

                manifest = _json.loads(manifest_path.read_text())
                personas.extend(
                    PersonaCard(
                        persona_id=persona["persona_id"],
                        name=persona["name"],
                        role=persona["role"],
                        segment=persona.get("segment"),
                        panel_kind=manifest["panel_kind"],
                        profile=persona.get("profile", {}),
                    )
                    for persona in manifest["personas"]
                )

    options = {
        o.id: OptionNodeModel(
            id=o.id,
            summary=o.summary,
            contributor=o.contributor,
            origin=o.origin,
            parents=o.parents,
            status=o.status,
            status_reason=o.status_reason,
        )
        for o in state.options.values()
    }
    assumptions = {
        a.id: AssumptionNode(
            id=a.id,
            statement=a.statement,
            impact=a.impact,
            uncertainty=a.uncertainty,
            score=a.score,
        )
        for a in state.assumptions.values()
    }
    artifacts = [
        ArtifactNode(
            id=a.id, path=a.path, kind=a.kind, content_hash=a.content_hash, assumption_ids=a.refs
        )
        for a in state.artifacts
        if not a.path.startswith("dossier/")
    ]

    def decision_for(stage: str, question_fragment: str) -> DecisionNode | None:
        found = None
        for node in decisions.values():  # insertion-ordered: keep the latest match
            if node.stage == stage and question_fragment in node.question:
                found = node
        return found

    pivotal = _pivotal_moments(transitions, options, decisions, moves, gates_rejected)
    reached = _STAGE_ORDER.index(state.stage)
    return DossierModel(
        session_id=state.session_id,
        name=state.name,
        mode=state.mode or "founder",
        status="complete" if state.stage == "complete" else "partial",
        stage=state.stage,
        dojo_banner=state.mode == "dojo",
        brief=state.brief,
        problem_statement=decision_for("define", "problem statement"),
        concept=decision_for("ideate", "concept"),
        recommendation=decision_for("test", "kill, iterate, or proceed"),
        evidence=evidence,
        insights=insights,
        options=options,
        decisions=decisions,
        assumptions=assumptions,
        artifacts=artifacts,
        personas=personas,
        abstentions=abstentions,
        model_traces=model_traces,
        transitions=transitions,
        moves=moves,
        pivotal_moments=pivotal,
        negative_space=NegativeSpace(
            research_debt=abstentions,
            suppressed_moves=[m for m in moves if not m.executed],
            stages_not_reached=_STAGE_ORDER[reached + 1 :] if state.stage != "complete" else [],
            gates_rejected=gates_rejected,
        ),
        token_usage=state.token_usage,
    )


def _pivotal_moments(
    transitions: list[TransitionNode],
    options: dict[str, OptionNodeModel],
    decisions: dict[str, DecisionNode],
    moves: list[MoveNode],
    gates_rejected: list[str],
) -> list[PivotalMoment]:
    pivotal: list[PivotalMoment] = []
    for t in transitions:
        if t.loopback:
            pivotal.append(
                PivotalMoment(
                    kind="loopback",
                    description=(
                        f"the run returned from {t.from_stage} to {t.to_stage}: {t.condition}"
                    ),
                    refs=t.refs,
                )
            )
    children: dict[str, int] = {}
    for option in options.values():
        for parent in option.parents:
            children[parent] = children.get(parent, 0) + 1
    for option in options.values():
        if option.status == "killed" and children.get(option.id):
            pivotal.append(
                PivotalMoment(
                    kind="killed_frontrunner",
                    description=(
                        f"option {option.summary!r} was built on by others but killed: "
                        f"{option.status_reason}"
                    ),
                    refs=[option.id],
                )
            )
    for decision in decisions.values():
        if decision.dissent:
            pivotal.append(
                PivotalMoment(
                    kind="adopted_with_dissent",
                    description=(
                        f"{decision.question!r} was resolved with dissent on record: "
                        + "; ".join(d.get("reservation", "") for d in decision.dissent)
                    ),
                    refs=[decision.id],
                )
            )
    for move in moves:
        if move.executed and move.move_id == "timebox_pivot":
            pivotal.append(
                PivotalMoment(
                    kind="timebox_pivot",
                    description="divergence was pivoted to convergence on novelty decay",
                    refs=[move.id],
                )
            )
    for reason in gates_rejected:
        pivotal.append(
            PivotalMoment(kind="gate_rejected", description=f"a gate was rejected: {reason}")
        )
    return pivotal
