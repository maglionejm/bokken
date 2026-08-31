"""Functional UI walkthrough: observed evidence, screenshots, review, honest skip."""

import base64
from pathlib import Path

import pytest

from bokken.journal import read_events
from bokken.orchestrator import create_session
from bokken.report.generate import generate_report
from bokken.stages import walkthrough as wt
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs, make_runner


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


class FakeWalker:
    def visit(self, app_url: str, *, max_pages: int = 6):
        assert app_url == "http://fake.local"
        return [
            wt.PageObservation(
                url="http://fake.local/",
                title="Shuttle Home",
                headings=["Plan your ride"],
                actions=["Upload schedule", "Sign in"],
                forms=1,
                console_errors=["manifest 404"],
                load_ms=240,
                screenshot_png=base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
                    "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
                ),
            ),
            wt.PageObservation(
                url="http://fake.local/plans",
                title="Plans",
                load_ms=180,
            ),
        ]


def run_session(tmp_path: Path, *, app_url: str | None) -> Path:
    inputs = make_inputs(tmp_path)
    if app_url:
        inputs["app_url"] = app_url
    session_dir = create_session(
        "walk-e2e",
        brief={**BRIEF, "inputs": inputs},
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    assert make_runner(session_dir, ScriptedProvider()).run().halt == "completed"
    return session_dir


def test_walkthrough_journals_observed_evidence_and_review(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(wt, "build_walker", lambda: FakeWalker())
    session_dir = run_session(tmp_path, app_url="http://fake.local")
    events = list(read_events(session_dir))
    observed = [
        e
        for e in events
        if e.type == "evidence.captured" and e.payload.get("source") == "ui_walkthrough"
    ]
    assert len(observed) == 2
    assert all(e.payload["confidence_class"] == "observed" for e in observed)
    shots = [e for e in events if e.payload.get("kind") == "ui_screenshot"]
    assert len(shots) == 1 and (session_dir / shots[0].payload["path"]).exists()
    review = next(e for e in events if e.payload.get("kind") == "ui_review")
    assert "Functional UI review" in (session_dir / review.payload["path"]).read_text()

    _, html_path = generate_report(session_dir)
    html = html_path.read_text()
    assert "Functional UI review" in html and "artifacts/ui/screen_01.png" in html


def test_missing_app_url_is_honest_research_debt(tmp_path) -> None:
    session_dir = run_session(tmp_path, app_url=None)
    events = list(read_events(session_dir))
    skip = next(
        e
        for e in events
        if e.type == "evidence.abstained"
        and str(e.payload["question"]).startswith("Functional UI walkthrough")
    )
    assert "app_url" in skip.payload["gap"]
    _, html_path = generate_report(session_dir)
    assert "Functional UI review" not in html_path.read_text()
