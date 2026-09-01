"""Structured-output schemas for stage-engine model calls."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from bokken.panel.corpus import Citation

ArtifactKind = Literal["concept_one_pager", "landing_copy", "storyboard", "demo_script"]


class InterviewQuestion(BaseModel):
    segment: str
    question: str


class InterviewProgram(BaseModel):
    questions: list[InterviewQuestion] = Field(min_length=1)


class FollowUp(BaseModel):
    question: str | None = None


class PersonaTurn(BaseModel):
    kind: Literal["grounded", "opinion", "abstain"]
    text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    gap: str = ""


class OutcomeDraft(BaseModel):
    statement: str
    job_step: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class OutcomeList(BaseModel):
    outcomes: list[OutcomeDraft] = Field(min_length=3, max_length=12)


class OutcomeScore(BaseModel):
    outcome_index: int
    importance: int = Field(ge=1, le=10)
    satisfaction: int = Field(ge=1, le=10)
    reason: str = ""


class OutcomeScores(BaseModel):
    scores: list[OutcomeScore] = Field(min_length=1)


class InsightDraft(BaseModel):
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)


class ClusterResult(BaseModel):
    insights: list[InsightDraft] = Field(min_length=1)


class CandidateStatement(BaseModel):
    statement: str
    insight_ids: list[str] = Field(default_factory=list)
    coverage: float = 0.0
    solution_shaped: bool = False
    reframe: str = ""


class Candidates(BaseModel):
    candidates: list[CandidateStatement] = Field(min_length=2)


class LoserNote(BaseModel):
    index: int
    why_lost: str


class Selection(BaseModel):
    winner_index: int
    losers: list[LoserNote] = Field(default_factory=list)


class IdeaDraft(BaseModel):
    summary: str
    private_thought: str = ""


class IdeaBatch(BaseModel):
    ideas: list[IdeaDraft] = Field(min_length=1)


class NoveltyVerdict(BaseModel):
    classification: Literal["novel_cluster", "variation", "duplicate"]


class Provocation(BaseModel):
    provocation: str


class VoteScore(BaseModel):
    option_id: str
    scores: dict[str, int] = Field(default_factory=dict)
    position: str = ""
    verdict: Literal["green", "amber", "red"] | None = None  # feasibility lens only
    first_slice: str = ""
    effort: Literal["S", "M", "L"] | None = None


class Votes(BaseModel):
    votes: list[VoteScore] = Field(min_length=1)


class SkepticChallenge(BaseModel):
    challenge: str


class AssumptionDraft(BaseModel):
    statement: str
    impact: Literal["low", "medium", "high"]
    uncertainty: Literal["low", "medium", "high"]


class AssumptionList(BaseModel):
    assumptions: list[AssumptionDraft] = Field(min_length=1)


class ArtifactPlanItem(BaseModel):
    kind: ArtifactKind
    assumption_indexes: list[int] = Field(min_length=1)


class FidelityChoice(BaseModel):
    artifacts: list[ArtifactPlanItem] = Field(min_length=1)
    rationale: str


class Evaluation(BaseModel):
    score: Literal["supported", "contradicted", "untested"]
    reaction: str


class Competitor(BaseModel):
    name: str
    url: str = ""
    what: str
    overlap: str  # how it overlaps with the selected concept


class MarketSignal(BaseModel):
    stat: str
    source_url: str


class MarketResearch(BaseModel):
    competitors: list[Competitor] = Field(default_factory=list)
    market_signals: list[MarketSignal] = Field(default_factory=list)
    regulatory: list[str] = Field(default_factory=list)
    pricing_benchmarks: list[str] = Field(default_factory=list)
    differentiation_risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class FeatureItem(BaseModel):
    name: str
    entry_hint: str = ""  # path or navigation hint
    expectation: str = ""  # what "works" looks like


class FeatureInventory(BaseModel):
    features: list[FeatureItem] = Field(min_length=1, max_length=10)


class UIAction(BaseModel):
    action: Literal["click", "fill", "press_enter", "goto", "done"]
    target_index: int | None = None
    value: str = ""
    verdict: Literal["works", "broken", "unclear"] | None = None  # for done
    finding: str = ""


class UIReview(BaseModel):
    markdown: str


class Recommendation(BaseModel):
    recommendation: Literal["kill", "iterate", "proceed"]
    confidence: str
    contradicts: str = ""
