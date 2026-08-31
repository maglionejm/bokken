"""A scripted, schema-faithful provider: the whole harness runs offline against it."""

from __future__ import annotations

import re
from collections import defaultdict

from bokken.models.router import ProviderResult
from bokken.panel.corpus import Citation
from bokken.stages import schemas as s

HEX32 = re.compile(r"\b[0-9a-f]{32}\b")
SOURCE = re.compile(r"\[source ([0-9a-f]{12}) \(")
QUOTA = re.compile(r"Produce (\d+) distinct")
PARTICIPANT = re.compile(r"You contribute as: (.+)")


class ScriptedProvider:
    """Dispatches on prompt_id; parses ids from the rendered prompt like a model would."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = defaultdict(int)

    def complete(self, *, model, prompt_id, rendered, schema, routing_class, stream, max_tokens):
        self.calls[prompt_id] += 1
        data = self._dispatch(prompt_id, rendered)
        if isinstance(data, str):
            text, payload = data, None
        else:
            text, payload = "", data
        return ProviderResult(
            text=text,
            data=payload,
            usage={"input_tokens": 50, "output_tokens": 20},
            request_id=f"fake-{prompt_id}-{self.calls[prompt_id]}",
            stop_reason="end_turn",
            model=model,
        )

    def _dispatch(self, prompt_id: str, rendered: str):
        n = self.calls[prompt_id]
        if prompt_id == "empathize/interview_program":
            segments = re.findall(r'"target_segments":\s*\[([^\]]*)\]', rendered)
            names = re.findall(r'"([^"]+)"', segments[0]) if segments else ["general"]
            return s.InterviewProgram(
                questions=[
                    s.InterviewQuestion(
                        segment=seg, question=f"Tell me about the last time {seg} hit this problem."
                    )
                    for seg in names
                ]
            )
        if prompt_id == "empathize/followup":
            return s.FollowUp(question=None)
        if prompt_id == "empathize/persona_turn":
            sources = SOURCE.findall(rendered)
            if not sources:
                return s.PersonaTurn(kind="abstain", gap="no corpus source covers this")
            if "pay" in rendered.lower():
                return s.PersonaTurn(kind="abstain", gap="no pricing data in the inputs")
            source = sources[n % len(sources)]
            return s.PersonaTurn(
                kind="grounded",
                text="the record shows unpredictable arrivals drive churn",
                citations=[Citation(source_id=source, start_line=1, end_line=1)],
            )
        if prompt_id == "define/cluster":
            evidence_ids = HEX32.findall(rendered)
            return s.ClusterResult(
                insights=[
                    s.InsightDraft(
                        statement="predictability beats speed for commuters",
                        evidence_ids=evidence_ids[:2],
                    )
                ]
            )
        if prompt_id == "define/candidates":
            insight_ids = HEX32.findall(rendered)
            return s.Candidates(
                candidates=[
                    s.CandidateStatement(
                        statement="Commuters cannot plan around unpredictable arrivals",
                        insight_ids=insight_ids[:1],
                        coverage=0.8,
                    ),
                    s.CandidateStatement(
                        statement="Build a push-notification ETA feature",
                        insight_ids=insight_ids[:1],
                        coverage=0.4,
                        solution_shaped=True,
                        reframe="make arrivals plannable for commuters",
                    ),
                ]
            )
        if prompt_id == "define/select":
            return s.Selection(
                winner_index=0, losers=[s.LoserNote(index=1, why_lost="weaker coverage")]
            )
        if prompt_id == "ideate/diverge":
            quota = int(QUOTA.search(rendered).group(1))
            who = PARTICIPANT.search(rendered).group(1).strip()
            return s.IdeaBatch(
                ideas=[
                    s.IdeaDraft(
                        summary=f"{who} option {i + 1}",
                        private_thought=f"{who} private reasoning {i + 1}",
                    )
                    for i in range(quota)
                ]
            )
        if prompt_id == "ideate/novelty":
            existing = rendered.count("\n", rendered.find("clusters:"))
            classification = "novel_cluster" if existing < 3 else "variation"
            return s.NoveltyVerdict(classification=classification)
        if prompt_id == "ideate/skeptic_challenge":
            return s.SkepticChallenge(challenge="the demand claim rests on one metric line")
        if prompt_id == "ideate/converge":
            option_ids = HEX32.findall(rendered)
            return s.Votes(
                votes=[
                    s.VoteScore(
                        option_id=option_ids[0],
                        scores={"desirability": 5, "feasibility": 4, "viability": 4},
                        position="strongest fit",
                    ),
                    s.VoteScore(
                        option_id=option_ids[-1],
                        scores={"desirability": 2, "feasibility": 3, "viability": 2},
                        position="risk: operators may reject it",
                    ),
                ]
            )
        if prompt_id == "prototype/assumptions":
            return s.AssumptionList(
                assumptions=[
                    s.AssumptionDraft(
                        statement="riders accept 5 minute detours",
                        impact="high",
                        uncertainty="high",
                    ),
                    s.AssumptionDraft(
                        statement="operators can publish schedules daily",
                        impact="medium",
                        uncertainty="low",
                    ),
                ]
            )
        if prompt_id == "prototype/fidelity":
            return s.FidelityChoice(
                artifacts=[s.ArtifactPlanItem(kind="landing_copy", assumption_indexes=[0, 1])],
                rationale="landing copy is the cheapest demand test for the detour assumption",
            )
        if prompt_id == "prototype/artifact":
            return "# Adaptive shuttle\n\nPlannable arrivals for your commute.\n"
        if prompt_id == "test/evaluate":
            score = "contradicted" if n == 1 else "supported"
            return s.Evaluation(score=score, reaction=f"reaction run {n}: {score}")
        if prompt_id == "test/recommend":
            return s.Recommendation(
                recommendation="iterate",
                confidence="medium",
                contradicts="the detour-tolerance assumption undermines the define insight",
            )
        if prompt_id == "handoff/specify":
            from bokken.handoff.schema import (
                CapabilityDraft,
                RequirementDraft,
                ScenarioDraft,
                SpecPackage,
                TaskGroupDraft,
            )

            return SpecPackage(
                why="Commuters cannot plan around unpredictable arrivals.",
                what_changes=["Introduce schedule publication for shuttle operators."],
                capabilities=[
                    CapabilityDraft(
                        name="Schedule Publication",  # normalizer must kebab this
                        purpose="Operators publish next-day schedules commuters can rely on.",
                        requirements=[
                            RequirementDraft(
                                name="Daily schedule publication",
                                statement="operators can publish the next day's schedule",
                                scenarios=[],  # normalizer must scaffold one
                                assumption_indexes=[1],  # supported assumption
                            ),
                            RequirementDraft(
                                name="Detour-based rerouting",
                                statement="The system SHALL reroute via rider detours.",
                                scenarios=[
                                    ScenarioDraft(
                                        name="Detour accepted",
                                        when="a detour is proposed",
                                        then="the rider accepts it",
                                    )
                                ],
                                assumption_indexes=[0],  # contradicted: must be dropped
                            ),
                        ],
                    )
                ],
                design_context="MVP for the adaptive shuttle concept.",
                design_decisions=["Publish schedules as static JSON first."],
                task_groups=[
                    TaskGroupDraft(
                        name="Schedule publication",
                        tasks=["Implement schedule publishing and verify with a test"],
                    )
                ],
            )
        raise AssertionError(f"ScriptedProvider has no handler for {prompt_id}")
