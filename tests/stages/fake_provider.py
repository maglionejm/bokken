"""A scripted, schema-faithful provider: the whole harness runs offline against it."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from bokken.models.router import MODELS, ProviderResult
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
        self.efforts: list[str | None] = []

    def complete(
        self,
        *,
        model,
        prompt_id,
        rendered,
        schema,
        routing_class,
        stream,
        max_tokens,
        web_search=False,
        reasoning_effort=None,
    ):
        self.calls[prompt_id] += 1
        self.efforts.append(reasoning_effort)
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
        if prompt_id == "empathize/outcomes":
            evidence_ids = HEX32.findall(rendered)
            return s.OutcomeList(
                outcomes=[
                    s.OutcomeDraft(
                        statement="Minimize the time it takes to plan around arrivals",
                        job_step="plan",
                        evidence_ids=evidence_ids[:1],
                    ),
                    s.OutcomeDraft(
                        statement="Increase certainty the shuttle arrives when promised",
                        job_step="ride",
                        evidence_ids=evidence_ids[:1],
                    ),
                    s.OutcomeDraft(
                        statement="Minimize the effort to recover from a missed shuttle",
                        job_step="recover",
                    ),
                ]
            )
        if prompt_id == "empathize/outcome_scores":
            return s.OutcomeScores(
                scores=[
                    s.OutcomeScore(
                        outcome_index=0, importance=9, satisfaction=2, reason="unpredictable"
                    ),
                    s.OutcomeScore(outcome_index=1, importance=8, satisfaction=3),
                    s.OutcomeScore(outcome_index=2, importance=5, satisfaction=5),
                ]
            )
        if prompt_id == "empathize/feature_inventory":
            assert "Interactive elements" in rendered  # home digest reached the model
            return s.FeatureInventory(
                features=[
                    s.FeatureItem(
                        name="Schedule upload",
                        entry_hint="/",
                        expectation="uploading a schedule confirms visibly",
                    ),
                    s.FeatureItem(
                        name="Plan browser",
                        entry_hint="/plans",
                        expectation="plans list renders",
                    ),
                ]
            )
        if prompt_id == "empathize/ui_action":
            if "(no steps yet)" in rendered:
                return s.UIAction(action="click", target_index=0)
            return s.UIAction(
                action="done",
                verdict="works" if "Schedule" in rendered else "broken",
                finding="confirmation banner appears" if "Schedule" in rendered else "list 404s",
            )
        if prompt_id == "empathize/ui_review":
            assert (
                "Per-feature functional test results" not in rendered
                or "Schedule upload" in rendered
                or "(no functional" in rendered
            )
            assert "[screen 1]" in rendered  # observed facts reach the reviewer
            return s.UIReview(
                markdown="# Functional UI review\n\nThe now-card loads in 240 ms - fast "
                "first contact.\n\n- home -> 1 console error -> erodes trust -> fix the "
                "manifest 404\n\nTop 3: fix the 404; label the upload button; add an "
                "empty-state hint.\n"
            )
        if prompt_id == "sidekick/context_query":
            # return the source-marked corpus lines verbatim (retrieval, not paraphrase)
            lines = [ln for ln in rendered.splitlines() if "[source " in ln]
            return "\n".join(lines[:6]) or "NO_COVERAGE"
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
            if "adversarial feasibility" in rendered:
                # The feasibility lens must actually see the product corpus.
                assert "Product corpus excerpt" in rendered
                return s.Votes(
                    votes=[
                        s.VoteScore(
                            option_id=option_ids[0],
                            scores={"feasibility": 5},
                            position="buildable on existing seams",
                            verdict="green",
                            effort="S",
                            first_slice="publish next-day schedule as static JSON",
                        ),
                        s.VoteScore(
                            option_id=option_ids[-1],
                            scores={"feasibility": 1},
                            position="not honestly buildable as scoped",
                            verdict="red",
                            effort="L",
                        ),
                    ]
                )
            if "RICE" in rendered:
                # Firewall: the PO lens never sees code.
                assert "Product corpus excerpt" not in rendered
                return s.Votes(
                    votes=[
                        s.VoteScore(
                            option_id=option_ids[0],
                            scores={"viability": 4},
                            position="RICE 3.0 (reach 9 x impact 2 x conf 1.0 / 6 pw)",
                        ),
                        s.VoteScore(
                            option_id=option_ids[-1],
                            scores={"viability": 2},
                            position="RICE 0.5; risk: operators may reject it",
                        ),
                    ]
                )
            return s.Votes(
                votes=[
                    s.VoteScore(
                        option_id=option_ids[0],
                        scores={"desirability": 5},
                        position="serves the top-opportunity outcome directly",
                    ),
                    s.VoteScore(
                        option_id=option_ids[-1],
                        scores={"desirability": 2},
                        position="weak fit with the outcome ranking",
                    ),
                ]
            )
        if prompt_id == "research/deep":
            return (
                "## Competitors\nRivalCo does schedule sharing (https://rival.example).\n"
                "## Market signals\n73% of EU households remain on fixed tariffs "
                "(https://stats.example/eu).\n## Open questions\nWill operators comply?\n"
            )
        if prompt_id == "research/structure":
            return s.MarketResearch(
                competitors=[
                    s.Competitor(
                        name="RivalCo",
                        url="https://rival.example",
                        what="schedule sharing",
                        overlap="partial - no rider guarantees",
                    )
                ],
                market_signals=[
                    s.MarketSignal(
                        stat="73% of EU households remain on fixed tariffs",
                        source_url="https://stats.example/eu",
                    )
                ],
                open_questions=["Will operators comply?"],
            )
        if prompt_id == "prototype/assumptions":
            if "allow_web_research" not in rendered:
                assert "{research}" not in rendered  # param rendered, not left raw
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
            if "wireframe_html" in rendered.split("Kind:")[1][:30]:
                assert "design tokens" in rendered or "/*" in rendered  # tokens reached the prompt
                return "<!doctype html><html><body><h1>Mock</h1></body></html>"
            return "# Adaptive shuttle\n\nPlannable arrivals for your commute.\n"
        if prompt_id == "test/evaluate":
            # Evaluators must see the prototype artifact, never a panel manifest.
            assert ("Adaptive shuttle" in rendered or "<h1>Mock</h1>" in rendered) and (
                '"panel_kind"' not in rendered
            )
            score = "contradicted" if n == 1 else "supported"
            return s.Evaluation(score=score, reaction=f"reaction run {n}: {score}")
        if prompt_id == "test/recommend":
            return s.Recommendation(
                recommendation="iterate",
                confidence="medium",
                contradicts="the detour-tolerance assumption undermines the define insight",
            )
        if prompt_id == "validate/next_turn":
            if "(interview not started)" in rendered:
                return s.InterviewerTurn(action="ask", question="Tell me about your last bill.")
            return s.InterviewerTurn(action="conclude", question="Thank you!")
        if prompt_id == "validate/rescore":
            assumption_ids = HEX32.findall(rendered.split("Real evidence")[0])
            evidence_ids = HEX32.findall(rendered.split("Real evidence")[1])
            return (
                s.Rescoring(
                    scores=[
                        s.RescoredAssumption(
                            assumption_id=assumption_ids[0],
                            score="supported",
                            rationale="the participant confirmed it happened last month",
                            evidence_ids=evidence_ids[:1],
                        )
                    ]
                )
                if assumption_ids and evidence_ids
                else s.Rescoring()
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


# What each routed model gets re-served on, same provider. `claude-fable-5` ->
# `claude-opus-4-8` is the charter's own server-side fallback; the rest give
# every lane a served model distinct from the requested one.
SERVED_INSTEAD: dict[str, str] = {
    "claude-fable-5": "claude-opus-4-8",
    "claude-opus-5": "claude-opus-4-7",
    "claude-sonnet-5": "claude-sonnet-4-6",
    "claude-haiku-4-5": "claude-sonnet-4-6",
    "gpt-5": "gpt-5.6-sol",
    "gpt-5-mini": "gpt-5.6-luna",
}


class FallbackProvider(ScriptedProvider):
    """Answers on a different model than routing asked for, on every lane.

    CLAUDE.md routes research and challenge to `claude-fable-5` with a
    server-side fallback to `claude-opus-4-8`: that fallback exists so it fires
    under load, and when it does, requested and served diverge for a
    configured, expected reason. Every other fake in this suite echoes the
    requested model straight back, which makes requested and served identical
    and leaves every test blind to a record naming the model routing asked for
    instead of the model that answered. This one keeps the difference visible.
    """

    def complete(self, **kwargs):
        requested = kwargs["model"]
        served = SERVED_INSTEAD.get(requested)
        # Echoing the request back would quietly defeat every test built on this.
        assert served is not None, f"no fallback model configured for {requested!r}"
        assert served != requested, f"{served!r} is not a fallback for {requested!r}"
        assert MODELS[served].provider == MODELS[requested].provider, (
            f"{served!r} does not belong to {requested!r}'s provider"
        )
        return replace(super().complete(**kwargs), model=served)
