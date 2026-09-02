"""DemoProvider: hand-crafted, publication-grade content for the Lanzadera demo.

Every answer is scripted (no network, no key, zero tokens) but plays by the
real rules: persona citations parse the real source markers from the rendered
prompt, so the dossier's evidence graph resolves against the bundled corpus.
"""

from __future__ import annotations

import re
from collections import defaultdict

from bokken.models.router import ProviderResult
from bokken.panel.corpus import Citation
from bokken.stages import schemas as s

HEX32 = re.compile(r"\b[0-9a-f]{32}\b")
SOURCE = re.compile(r"\[source ([0-9a-f]{12}) \((\w+)\)")
QUOTA = re.compile(r"Produce (\d+) distinct")
PARTICIPANT = re.compile(r"You contribute as: (.+)")

PERSONA_ANSWERS = [
    (
        "The window is the whole product for me. The README calls plus-minus six "
        "minutes 'the product's core covenant' - and my own months say the covenant "
        "is slipping: compliance fell from 87% to 71% between March and August while "
        "delay tickets quadrupled from 96 to 402. I plan childcare around that "
        "number. When it stretches to fifteen real minutes, I miss the 7:40 and the "
        "next seat is 9:05.",
        "discussion",
    ),
    (
        "What makes me angry is not the delay - it is the green tick. The app says "
        "'ventana cumplida' even when the van was nine minutes late, because it "
        "counts from the dawn re-plan, not from what it promised me the night "
        "before. I can plan around honesty. I cannot plan around a green tick that "
        "lies.",
        "discussion",
    ),
    (
        "The 400-metre pickup rule reads reasonable in the README, but my corner "
        "moved behind the market one Monday after a 'route optimization' and nobody "
        "told me. Six minutes walking, uphill, on top of a 3.20-euro ride, while the "
        "Cercanias costs 1.85. Three days out of five the train now wins.",
        "discussion",
    ),
    (
        "The numbers say riders like me are already voting: average rides per rider "
        "fell from 31.2 to 23.1 in six months and the monthly-pass share slid from "
        "46% to 38%. The app still pushes the 89-euro pass at me like I commute ten "
        "trips a week. Charge me for what I use and I stay.",
        "metrics",
    ),
    (
        "Booking changes close at 21:00 the night before - that is exactly when the "
        "app should tell me tomorrow's truth: my pickup point and an honest window. "
        "If tomorrow will be wide, say so and let me take the 7:20 van instead. The "
        "information exists; the route is re-optimized nightly.",
        "code",
    ),
]

OUTCOMES = [
    (
        "Increase the likelihood that the pickup window promised at 21:00 is the "
        "window that actually happens the next morning",
        "plan",
    ),
    (
        "Minimize the surprise of a pickup point that moved overnight - the rider "
        "knows the point and the walk before going to bed",
        "plan",
    ),
    (
        "Minimize the cost of a missed pickup - a same-morning recovery option "
        "instead of a 90-minute gap",
        "recover",
    ),
    (
        "Increase trust that the app's on-time indicator reflects the promise made "
        "to the rider, not the re-planned route",
        "trust",
    ),
    ("Minimize the money a 2-3 day rider wastes versus pay-per-use reality", "pay"),
    (
        "Increase the perceived fairness of route optimization - riders understand "
        "why their pickup changed",
        "trust",
    ),
    ("Minimize the door-to-van walk variance across weeks", "plan"),
]

# (importance, satisfaction) per persona index for each outcome: engineered so
# outcome 3 (honest indicator) wins at 16.0 with a segment spike.
SCORES = {
    0: [(9, 3), (8, 4), (9, 3)],
    1: [(8, 3), (9, 2), (7, 4)],
    2: [(8, 2), (6, 3), (7, 3)],
    3: [(9, 2), (9, 2), (9, 2)],
    4: [(5, 4), (9, 3), (4, 5)],
    5: [(7, 4), (8, 3), (6, 4)],
    6: [(7, 3), (7, 4), (6, 4)],
}

IDEAS = {
    "seed": [
        "'Ventana honesta': at 21:00, with the route already optimized, push the "
        "real pickup point and an honest window for tomorrow - including 'wide "
        "window (12 min) on your street tomorrow' - with a one-tap switch to an "
        "earlier van when the window is wide [serves: O0, O1, O3]",
        "A missed-pickup rescue: if the van leaves without you, one tap books the "
        "next passing van within 20 minutes at no charge, twice per month "
        "[serves: O2]",
        "Route-change receipts: when a pickup point moves, the notification says "
        "why ('two new riders on Calle Mayor') and shows the new walk time "
        "[serves: O1, O5]",
    ],
    "alt": [
        "A flexible 24-ride pack priced for 2-3 day riders, replacing the "
        "one-size monthly pass banner [serves: O4]",
        "Live 'promise vs actual' indicator: the on-time tick compares against "
        "what was promised at 21:00, never against the dawn re-plan "
        "[serves: O3]",
        "Walk-distance cap preference: riders opt into 'never move my point "
        "beyond 250 m' in exchange for a slightly earlier pickup [serves: O6]",
    ],
    "wild": [
        "Weekly window report: every Friday, your street's real window compliance "
        "vs promise, published in the app [serves: O3]",
        "Van-full transparency: show seat load at booking so riders self-shift to "
        "emptier vans [serves: O0]",
        "Neighborhood route council: riders vote monthly on the pickup-point map [serves: O5]",
    ],
}

ASSUMPTIONS = [
    ("Riders will read a 21:00 notification the night before commuting", "high", "medium"),
    ("An honest 'wide window' warning reduces anger more than it reduces bookings", "high", "high"),
    (
        "The route engine can commit a next-morning window at 21:00 within +/-2 min accuracy",
        "high",
        "high",
    ),
    ("Riders on wide-window days will switch vans rather than churn", "high", "high"),
    ("The 'promise vs actual' tick can be computed from data already stored", "medium", "low"),
    ("Marta's segment (daily pass holders) values honesty over raw punctuality", "high", "medium"),
    ("Diego's segment will not abuse a free missed-pickup rescue", "medium", "medium"),
    ("Publishing real compliance numbers will not be weaponized by competitors", "medium", "high"),
    ("Support ticket volume drops when windows are honest (402/mo baseline)", "medium", "high"),
    (
        "The 21:00 booking-change deadline is the right moment for the truth push",
        "medium",
        "medium",
    ),
]

WIREFRAME = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Lanzadera - Ventana honesta</title>
<style>
:root { --lz-ink:#1c2733; --lz-paper:#f6f8fa; --lz-brand:#0f766e; --lz-brand-soft:#ccfbf1;
--lz-alert:#b45309; --lz-radius:10px; --lz-font:-apple-system,"Segoe UI",Roboto,sans-serif; }
body{font-family:var(--lz-font);color:var(--lz-ink);background:var(--lz-paper);
margin:0;padding:24px;max-width:420px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:var(--lz-radius);
padding:16px;margin-bottom:14px}
.pickup-window{font-variant-numeric:tabular-nums;font-size:28px;font-weight:700}
.delay{color:var(--lz-alert)}
.badge-route{background:var(--lz-brand-soft);color:var(--lz-brand);
border-radius:999px;padding:2px 10px;font-size:12px}
.btn-primary{background:var(--lz-brand);color:#fff;border:none;
border-radius:var(--lz-radius);padding:12px 20px;font-weight:600;width:100%;font-size:16px}
small{color:#64748b}
</style></head><body>
<div class="card">
  <span class="badge-route">Ruta M-403 · manana</span>
  <p class="pickup-window">07:38 - 07:46</p>
  <p><b>Tu parada:</b> Calle Mayor, 12 (la de siempre · 3 min andando)</p>
  <small>Confirmado a las 21:00 con la ruta de manana ya optimizada.</small>
</div>
<div class="card">
  <p class="delay"><b>Manana tu ventana es ancha (12 min).</b></p>
  <p>Hay obras en la M-40. Si necesitas puntualidad, la van de las 07:20
  mantiene una ventana de 6 min.</p>
  <button class="btn-primary">Cambiarme a la van de las 07:20</button>
  <small>Sin coste · puedes volver a tu van habitual cuando quieras</small>
</div>
</body></html>
"""

LANDING = """# Lanzadera - Ventana honesta

**HILL** - WHO: the daily commuter who plans childcare around a pickup window
· WHAT: knows tonight, at 21:00, exactly where and when tomorrow's van picks
them up - including when the window will be wide - with a one-tap switch to a
tighter van · WOW: the on-time tick now measures the promise, not the re-plan;
honesty becomes the feature.

We believe daily pass holders will forgive wide windows they were warned about,
measured by: missed-pickup support tickets (402/month baseline) dropping 30%
and pass churn (345/month) flattening within two cycles.

## Manana, sin sorpresas

A las 21:00, cuando la ruta ya esta optimizada, te contamos la verdad:
tu parada, tu ventana real, y una alternativa si manana viene ancho.

- Tu ventana de manana, confirmada esta noche
- Si sera ancha, te lo decimos - y te ofrecemos la van de las 07:20
- El tick verde ahora mide lo que te prometimos, no lo que replanificamos
"""


class DemoProvider:
    """Scripted provider for `bokken demo`: zero network, zero tokens, real rules."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = defaultdict(int)

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
        data = self._dispatch(prompt_id, rendered)
        text, payload = (data, None) if isinstance(data, str) else ("", data)
        return ProviderResult(
            text=text,
            data=payload,
            usage={"input_tokens": 0, "output_tokens": 0},
            request_id=f"demo-{prompt_id}-{self.calls[prompt_id]}",
            stop_reason="end_turn",
            model=model,
        )

    def _dispatch(self, prompt_id: str, rendered: str):
        n = self.calls[prompt_id]
        if prompt_id == "empathize/interview_program":
            return s.InterviewProgram(
                questions=[
                    s.InterviewQuestion(
                        segment="daily pass commuters",
                        question="Walk me through the last morning the pickup window "
                        "let you down - what did that cost you?",
                    ),
                    s.InterviewQuestion(
                        segment="daily pass commuters",
                        question="What does the app tell you the night before, and "
                        "what do you wish it told you?",
                    ),
                    s.InterviewQuestion(
                        segment="flexible pay-per-ride commuters",
                        question="When the train wins over the shuttle, what tipped "
                        "the decision that day?",
                    ),
                ]
            )
        if prompt_id == "empathize/followup":
            return s.FollowUp(question=None)
        if prompt_id == "sidekick/context_query":
            lines = [ln for ln in rendered.splitlines() if "[source " in ln]
            return "\n".join(lines[:8]) or "NO_COVERAGE"
        if prompt_id == "empathize/persona_turn":
            sources = SOURCE.findall(rendered)
            if not sources:
                return s.PersonaTurn(kind="abstain", gap="no corpus source covers this")
            text, want_kind = PERSONA_ANSWERS[(n - 1) % len(PERSONA_ANSWERS)]
            match = next((sid for sid, kind in sources if kind == want_kind), sources[0][0])
            return s.PersonaTurn(
                kind="grounded",
                text=text,
                citations=[Citation(source_id=match, start_line=1, end_line=3)],
            )
        if prompt_id == "empathize/outcomes":
            evidence_ids = HEX32.findall(rendered)
            return s.OutcomeList(
                outcomes=[
                    s.OutcomeDraft(
                        statement=stmt,
                        job_step=step,
                        evidence_ids=evidence_ids[i % max(len(evidence_ids), 1) :][:1]
                        if evidence_ids
                        else [],
                    )
                    for i, (stmt, step) in enumerate(OUTCOMES)
                ]
            )
        if prompt_id == "empathize/outcome_scores":
            idx = (n - 1) % 3
            return s.OutcomeScores(
                scores=[
                    s.OutcomeScore(
                        outcome_index=o,
                        importance=SCORES[o][idx][0],
                        satisfaction=SCORES[o][idx][1],
                        reason=(
                            "the green tick says 'cumplida' while I stand in the cold"
                            if o == 3 and idx == 0
                            else ""
                        ),
                    )
                    for o in SCORES
                ]
            )
        if prompt_id == "empathize/ui_review":
            return s.UIReview(markdown="(demo run: no live app attached)\n")
        if prompt_id == "define/cluster":
            evidence_ids = HEX32.findall(rendered)
            return s.ClusterResult(
                insights=[
                    s.InsightDraft(
                        statement="Daily pass holders are not churning over delays - "
                        "they are churning over a dishonest on-time indicator: the "
                        "tick measures the dawn re-plan, the rider measures the "
                        "21:00 promise (compliance fell 87%→71% while tickets went "
                        "96→402/month)",
                        evidence_ids=evidence_ids[:3],
                    ),
                    s.InsightDraft(
                        statement="Pickup points that move silently convert the "
                        "route engine's efficiency into perceived unfairness - a "
                        "one-line 'why' would flip the same event from tax to "
                        "service",
                        evidence_ids=evidence_ids[2:5] or evidence_ids[:1],
                    ),
                    s.InsightDraft(
                        statement="Flexible riders (2-3 days/week, rides/rider down "
                        "31.2→23.1) are mispriced by a pass built for 10 trips and "
                        "defect to a 1.85-euro train without complaining",
                        evidence_ids=evidence_ids[3:6] or evidence_ids[:1],
                    ),
                ]
            )
        if prompt_id == "define/candidates":
            insight_ids = HEX32.findall(rendered)
            return s.Candidates(
                candidates=[
                    s.CandidateStatement(
                        statement="Daily pass commuters (46%→38% of riders) plan "
                        "their mornings around a ±6-minute promise the product no "
                        "longer keeps (71% compliance) nor admits to - the trust "
                        "gap, not the delay itself, is driving the 345/month churn",
                        insight_ids=insight_ids[:2],
                        coverage=0.85,
                    ),
                    s.CandidateStatement(
                        statement="Build a night-before notification with tomorrow's window",
                        insight_ids=insight_ids[:1],
                        coverage=0.5,
                        solution_shaped=True,
                        reframe="give riders an honest picture of tomorrow's commute "
                        "before the booking deadline",
                    ),
                    s.CandidateStatement(
                        statement="Flexible riders lack a fair price, pushing them "
                        "to rail on marginal days",
                        insight_ids=insight_ids[2:3] or insight_ids[:1],
                        coverage=0.55,
                    ),
                ]
            )
        if prompt_id == "define/select":
            return s.Selection(
                winner_index=0,
                losers=[
                    s.LoserNote(
                        index=1,
                        why_lost="solution-shaped; reframed and folded "
                        "into the winner's opportunity space",
                    ),
                    s.LoserNote(
                        index=2,
                        why_lost="real but narrower: pricing pain "
                        "affects 2-3 day riders; the trust gap affects every "
                        "segment and compounds monthly",
                    ),
                ],
            )
        if prompt_id == "ideate/diverge":
            quota = int(QUOTA.search(rendered).group(1))
            who = PARTICIPANT.search(rendered).group(1).strip()
            bank = IDEAS["seed"] if n == 1 else IDEAS["alt"] if n == 2 else IDEAS["wild"]
            return s.IdeaBatch(
                ideas=[
                    s.IdeaDraft(
                        summary=bank[i % len(bank)],
                        private_thought=f"{who}: weighing against the 21:00 deadline",
                    )
                    for i in range(quota)
                ]
            )
        if prompt_id == "ideate/novelty":
            existing = rendered.count("\n", rendered.find("clusters:"))
            return s.NoveltyVerdict(classification="novel_cluster" if existing < 7 else "variation")
        if prompt_id == "ideate/skeptic_challenge":
            return s.SkepticChallenge(
                challenge="The weakest claim on the table is that honesty reduces "
                "churn: the record proves riders are angry about the lying tick, "
                "but no evidence shows a warned rider stays. A 'wide window' push "
                "at 21:00 might simply move the churn decision to bedtime. The "
                "cheapest test: measure switch-vs-cancel behavior on the one-tap "
                "van change before believing the retention story."
            )
        if prompt_id == "ideate/converge":
            option_ids = HEX32.findall(rendered)
            if "adversarial feasibility" in rendered:
                return s.Votes(
                    votes=[
                        s.VoteScore(
                            option_id=option_ids[0],
                            scores={"feasibility": 5},
                            position="The route engine already commits a plan "
                            "nightly; surfacing it at 21:00 is exposure, not "
                            "invention. The README confirms changes close at "
                            "21:00 - the data and the moment already align.",
                            verdict="green",
                            effort="S",
                            first_slice="push tomorrow's point+window at 21:00, "
                            "read-only (no van switching yet)",
                        ),
                        s.VoteScore(
                            option_id=option_ids[-1],
                            scores={"feasibility": 1},
                            position="A rider-voted pickup map fights the "
                            "optimizer head-on; every vote becomes a constraint "
                            "the engine must not break. Not honestly buildable "
                            "as scoped.",
                            verdict="red",
                            effort="L",
                        ),
                    ]
                )
            if "RICE" in rendered:
                return s.Votes(
                    votes=[
                        s.VoteScore(
                            option_id=option_ids[0],
                            scores={"viability": 5},
                            position="RICE 4.2: reach 9 (every active rider gets "
                            "the 21:00 push), impact 3 (attacks the top-ranked "
                            "outcome, opp 16.0), confidence 0.7, effort 4.5 pw",
                        ),
                        s.VoteScore(
                            option_id=option_ids[-1],
                            scores={"viability": 2},
                            position="RICE 0.6: monthly governance overhead for "
                            "a fairness perception the receipts idea buys "
                            "cheaper",
                        ),
                    ]
                )
            return s.Votes(
                votes=[
                    s.VoteScore(
                        option_id=option_ids[0],
                        scores={"desirability": 5},
                        position="Directly serves the 16.0 outcome and Marta's "
                        "exact words: 'I can plan around honesty'",
                    ),
                    s.VoteScore(
                        option_id=option_ids[-1],
                        scores={"desirability": 2},
                        position="Council governance is nobody's morning problem",
                    ),
                ]
            )
        if prompt_id == "prototype/assumptions":
            return s.AssumptionList(
                assumptions=[
                    s.AssumptionDraft(statement=st, impact=imp, uncertainty=unc)
                    for st, imp, unc in ASSUMPTIONS
                ]
            )
        if prompt_id == "prototype/fidelity":
            return s.FidelityChoice(
                artifacts=[
                    s.ArtifactPlanItem(kind="wireframe_html", assumption_indexes=[0, 1, 3]),
                    s.ArtifactPlanItem(kind="landing_copy", assumption_indexes=[1, 5]),
                ],
                rationale="The riskiest cluster is behavioral: will a warned rider "
                "switch vans instead of churning (assumptions 1 and 3)? A wireframe "
                "of the 21:00 push on the product's own design tokens makes the "
                "moment concrete enough to test the switch behavior; landing copy "
                "tests whether 'honesty as a feature' is a message pass holders "
                "buy. Both are days, not weeks.",
            )
        if prompt_id == "prototype/artifact":
            return WIREFRAME if "wireframe_html" in rendered.split("Kind:")[1][:30] else LANDING
        if prompt_id == "research/deep":
            return (
                "## Competitors\nDEMO DATA (fictional, for illustration): BusUp "
                "operates B2B commuter shuttles (https://demo.example/busup) - "
                "windows are contractual, not consumer-facing. Renfe Cercanias "
                "(https://demo.example/cercanias) publishes real-time compliance.\n"
                "## Market signals\nDEMO: 62% of shuttle churners in a 2026 mobility "
                "survey cite reliability communication, not reliability itself "
                "(https://demo.example/mobility-survey).\n## Open questions\n"
                "Whether honesty-forward messaging has precedent in transit apps.\n"
            )
        if prompt_id == "research/structure":
            return s.MarketResearch(
                competitors=[
                    s.Competitor(
                        name="BusUp (demo data)",
                        url="https://demo.example/busup",
                        what="B2B commuter shuttles with contractual SLAs",
                        overlap="partial - no consumer-facing window promise",
                    ),
                    s.Competitor(
                        name="Renfe Cercanias (demo data)",
                        url="https://demo.example/cercanias",
                        what="publishes real-time punctuality",
                        overlap="the substitute riders defect to at 1.85 EUR",
                    ),
                ],
                market_signals=[
                    s.MarketSignal(
                        stat="DEMO: 62% of shuttle churners cite reliability "
                        "communication, not reliability itself",
                        source_url="https://demo.example/mobility-survey",
                    ),
                ],
                differentiation_risks=[
                    "DEMO: honesty-forward messaging is easily copied; the moat is "
                    "the nightly engine commitment, not the copy",
                ],
                open_questions=["Does a warned rider switch vans or cancel?"],
            )
        if prompt_id == "test/evaluate":
            script = [
                "supported",
                "supported",
                "contradicted",
                "supported",
                "untested",
                "supported",
                "untested",
                "untested",
                "contradicted",
                "untested",
            ]
            score = script[(n - 1) % len(script)]
            reactions = {
                "supported": "Looking at the mock: the 07:20 switch button under an "
                "honest 'ventana ancha' warning is exactly what I asked for - I "
                "would tap it.",
                "contradicted": "Honestly? If the app tells me at 21:00 that "
                "tomorrow is a 12-minute window, some nights I will just book the "
                "train right then. The warning helps the product's honesty, not "
                "necessarily its retention.",
                "untested": "I cannot judge this from a mock - it depends on how "
                "the engine behaves over weeks, and no screen can show me that.",
            }
            return s.Evaluation(score=score, reaction=reactions[score])
        if prompt_id == "test/recommend":
            return s.Recommendation(
                recommendation="iterate",
                confidence="Register: 4 supported, 2 contradicted, 4 untested of 10. "
                "What survives is the demand side - riders want the 21:00 truth and "
                "say they would use the van switch. What broke is the core "
                "retention bet: two personas independently said an honest wide-"
                "window warning may trigger same-night defection to rail, which "
                "strikes assumption 2 and the concept's business case. Next step "
                "for the founder: ship the read-only slice (point + window at "
                "21:00, no switch) to 50 riders and measure next-morning behavior "
                "before building the switching flow.",
                contradicts="the 'honesty reduces churn' assumption is contradicted "
                "by the same evidence that supports demand for honesty",
            )
        if prompt_id == "handoff/specify":
            from bokken.handoff.schema import (
                CapabilityDraft,
                RequirementDraft,
                ScenarioDraft,
                SliceDraft,
                SpecPackage,
                TaskGroupDraft,
            )

            return SpecPackage(
                why="The top-ranked outcome (opportunity 16.0) is trusting the "
                "pickup window promise; the register supports demand for a 21:00 "
                "honest push while contradicting the retention assumption - so the "
                "MVP ships the smallest honest slice and instruments the churn "
                "question instead of assuming it.",
                what_changes=[
                    "Expose the nightly route commitment to riders at "
                    "21:00 with an honest window classification."
                ],
                capabilities=[
                    CapabilityDraft(
                        name="night-before-truth",
                        purpose="Riders receive tomorrow's pickup point and an "
                        "honestly classified window at 21:00, when the route is "
                        "committed and changes are still possible.",
                        requirements=[
                            RequirementDraft(
                                name="Nightly window push",
                                statement="The system SHALL notify each booked rider "
                                "at 21:00 with tomorrow's pickup point, window, and "
                                "a wide-window flag when the predicted window "
                                "exceeds 8 minutes.",
                                scenarios=[
                                    ScenarioDraft(
                                        name="Wide window disclosed",
                                        when="tomorrow's predicted window exceeds 8 minutes",
                                        then="the 21:00 notification says so explicitly "
                                        "and links the earlier-van alternative",
                                    )
                                ],
                                assumption_indexes=[0, 2],
                            ),
                        ],
                        slices=[
                            SliceDraft(
                                name="read-only push",
                                size="S",
                                what="point + window + wide flag, no van "
                                "switching; instrument opens and "
                                "next-morning behavior",
                            )
                        ],
                        dependencies=["route engine's nightly commitment timestamp"],
                    ),
                    CapabilityDraft(
                        name="honest-ontime-indicator",
                        purpose="The on-time tick measures the 21:00 promise, never "
                        "the dawn re-plan.",
                        requirements=[
                            RequirementDraft(
                                name="Promise-based compliance",
                                statement="The system SHALL compute window compliance "
                                "against the window communicated at 21:00.",
                                scenarios=[
                                    ScenarioDraft(
                                        name="Late van shows honestly",
                                        when="the van arrives outside the promised window",
                                        then="the trip is marked missed even if it met "
                                        "the re-planned route",
                                    )
                                ],
                                assumption_indexes=[4],
                            ),
                        ],
                        slices=[
                            SliceDraft(
                                name="indicator flip",
                                size="S",
                                what="swap the comparison baseline; "
                                "backfill 90 days for the rider's "
                                "history view",
                            )
                        ],
                        dependencies=["night-before-truth (the promise to measure)"],
                    ),
                ],
                design_context="Instrument the contradicted retention assumption "
                "instead of building on it.",
                design_decisions=[
                    "Read-only first: no van switching until switch-vs-cancel behavior is measured."
                ],
                task_groups=[
                    TaskGroupDraft(
                        name="Read-only slice",
                        tasks=[
                            "Ship the 21:00 push to a 50-rider cohort and verify "
                            "delivery + open instrumentation"
                        ],
                    )
                ],
                sequencing=[
                    "night-before-truth read-only slice - quick win, zero "
                    "dependencies, answers the contradicted assumption",
                    "honest-ontime-indicator - flips the trust story once "
                    "the promise exists to measure against",
                ],
            )
        raise AssertionError(f"DemoProvider has no handler for {prompt_id}")
