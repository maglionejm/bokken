"""The demo run: one command, zero keys, a full Lanzadera engagement."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

DEMO_BRIEF = {
    "problem_space": "Lanzadera is an on-demand commuter shuttle for Spanish "
    "suburbs whose core covenant is a +/-6-minute pickup window. Compliance and "
    "ridership are sliding; the space to explore: what between the promise and "
    "the morning reality is driving pass holders back to the train.",
    "constraints": [
        "the nightly route optimization stays (it is the unit economics)",
        "Spanish-first UI, plain language",
        "no new hardware or driver-side changes",
    ],
    "target_segments": ["daily pass commuters", "flexible pay-per-ride commuters"],
    "success_criteria": ["pass churn flattens", "delay support tickets drop 30%"],
    "risk_tolerance": "medium",
    "allow_web_research": True,
    "inputs": {
        "repo": str(FIXTURES / "repo"),
        # A static mock of the product: with the [ui] extra installed the real
        # walkthrough and feature tests run against it - still no network.
        "app_url": (FIXTURES / "app" / "index.html").as_uri(),
        "metrics": [str(FIXTURES / "kpis.csv")],
        "discussions": [
            str(FIXTURES / "interview_marta.md"),
            str(FIXTURES / "interview_diego.md"),
        ],
    },
}


def run_demo(name: str = "demo") -> dict:
    """Create, run, and finalize the demo session offline. Returns summary paths."""
    from bokken.demo.provider import DemoProvider
    from bokken.handoff import finalize_session
    from bokken.kata import MVP_MOVES, Kata
    from bokken.models import ModelRouter
    from bokken.orchestrator import Runner, create_session
    from bokken.stages import engine_suite

    provider = DemoProvider()
    factory = lambda store: ModelRouter(store, provider)  # noqa: E731
    session_dir = create_session(
        name,
        brief=DEMO_BRIEF,
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}, "demo": True},
    )
    runner = Runner(
        session_dir,
        engines=engine_suite(factory),
        input_port=None,
        kata_factory=lambda store: Kata(MVP_MOVES, store),
    )
    result = runner.run()
    finalization = finalize_session(session_dir, factory)
    return {
        "session_dir": session_dir,
        "halt": result.halt,
        "finalization": finalization.summary(),
        "report_html": session_dir / "report" / "report.html",
        "report_pptx": session_dir / "report" / "report.pptx",
        "dossier": session_dir / "dossier" / "dossier.md",
    }
