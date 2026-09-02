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
    def visit(self, app_url: str, *, max_pages: int = 12, seed_paths=None):
        assert app_url == "http://fake.local"
        assert seed_paths is not None  # repo routes reach the walker
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


class FakeTester:
    def start(self, app_url):
        assert app_url == "http://fake.local"

    def goto(self, url):
        self.here = url

    def digest(self):
        return (
            "URL: http://fake.local\nInteractive elements (index · tag · text):"
            "\n  [0] button · Upload Schedule"
        )

    def act(self, action):
        return "ok (navigated to http://fake.local/done)"

    def screenshot(self):
        import base64

        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
            "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
        )

    def close(self):
        pass


def test_walkthrough_journals_observed_evidence_and_review(tmp_path, monkeypatch) -> None:
    from bokken.stages import ui_tests

    monkeypatch.setattr(ui_tests, "build_tester", lambda: FakeTester())
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
    assert len(shots) == 3 and all((session_dir / s.payload["path"]).exists() for s in shots)
    assert any("feature_" in s.payload["path"] for s in shots)
    review = next(e for e in events if e.payload.get("kind") == "ui_review")
    assert "Functional UI review" in (session_dir / review.payload["path"]).read_text()

    events2 = events
    feature_evidence = [
        e
        for e in events2
        if e.type == "evidence.captured" and e.payload.get("source") == "ui_feature_test"
    ]
    assert len(feature_evidence) == 2
    assert all(e.payload["confidence_class"] == "observed" for e in feature_evidence)
    kinds2 = [e.payload.get("kind") for e in events2 if e.type == "artifact.generated"]
    assert kinds2.count("ui_feature_tests") == 2
    tests_md = (session_dir / "artifacts/ui/ui_feature_tests.md").read_text()
    assert "Schedule upload" in tests_md and "WORKS" in tests_md

    _, html_path = generate_report(session_dir)
    html = html_path.read_text()
    assert "functional ui review" in html  # chapter kicker
    assert "data:image/png;base64," in html  # self-contained screenshots
    assert "Schedule upload" in html and "broken" in html  # feature cards with verdicts


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
    assert "functional ui review" not in html_path.read_text()


def test_concept_research_authorized_path(tmp_path, monkeypatch) -> None:
    from bokken.journal import read_events
    from bokken.orchestrator import create_session

    inputs = make_inputs(tmp_path)
    session_dir = create_session(
        "research-e2e",
        brief={**BRIEF, "allow_web_research": True, "inputs": inputs},
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    assert make_runner(session_dir, ScriptedProvider()).run().halt == "completed"
    events = list(read_events(session_dir))
    research_calls = [
        e for e in events if e.type == "model.called" and e.payload["prompt_id"] == "research/deep"
    ]
    assert research_calls and research_calls[0].payload["web_search"] is True
    reported = [
        e
        for e in events
        if e.type == "evidence.captured"
        and e.payload["confidence_class"] == "reported"
        and "http" in str(e.payload.get("source", ""))
    ]
    assert reported, "sourced findings journaled as reported evidence"
    kinds = [e.payload.get("kind") for e in events if e.type == "artifact.generated"]
    assert kinds.count("market_research") == 2  # md + json
    md = (session_dir / "artifacts/research/market_research.md").read_text()
    assert "RivalCo" in md and "https://stats.example/eu" in md


def test_concept_research_skipped_without_flag(tmp_path) -> None:
    from bokken.journal import read_events

    session_dir = run_session(tmp_path, app_url=None)  # BRIEF has no flag
    events = list(read_events(session_dir))
    skip = [
        e
        for e in events
        if e.type == "evidence.abstained"
        and str(e.payload["question"]).startswith("Concept research")
    ]
    assert skip and "allow_web_research" in skip[0].payload["gap"]
    assert not any(e.type == "model.called" and e.payload.get("web_search") for e in events)


def test_large_corpus_is_delegated_to_the_sidekick(tmp_path, monkeypatch) -> None:
    from bokken.journal.store import JournalStore
    from bokken.models import ModelRouter
    from bokken.orchestrator import create_session
    from bokken.stages.persona_gen import DELEGATE_THRESHOLD_CHARS, RouterTurnGenerator

    session_dir = create_session("sidekick-unit", brief=BRIEF, mode="dojo", gate_policy="none")
    provider = ScriptedProvider()
    with JournalStore.open(session_dir) as store:
        generator = RouterTurnGenerator(ModelRouter(store, provider))
        big_context = "\n".join(
            f"[source abcdef123456 (code) L{i}-L{i}] line {i}" for i in range(12_000)
        )
        assert len(big_context) > DELEGATE_THRESHOLD_CHARS
        sliced = generator._sliced_context("what does the code do?", big_context)
    assert provider.calls["sidekick/context_query"] == 1
    assert "[source " in sliced and len(sliced) < len(big_context) / 10
    events = list(read_events(session_dir))
    call = next(e for e in events if e.type == "model.called")
    assert call.payload["routing_class"] == "sidekick"
    assert call.payload["model"] == "claude-opus-5"


def test_retrieval_is_reused_across_personas_asking_the_same_question(tmp_path) -> None:
    """Every persona on the panel asks one question over one corpus: retrieval runs
    once, so all their turns carry a byte-identical cacheable corpus prefix."""
    from bokken.journal.store import JournalStore
    from bokken.models import ModelRouter
    from bokken.orchestrator import create_session
    from bokken.stages.persona_gen import DELEGATE_THRESHOLD_CHARS, RouterTurnGenerator

    session_dir = create_session("sidekick-reuse", brief=BRIEF, mode="dojo", gate_policy="none")
    provider = ScriptedProvider()
    with JournalStore.open(session_dir) as store:
        generator = RouterTurnGenerator(ModelRouter(store, provider))
        big_context = "x" * (DELEGATE_THRESHOLD_CHARS + 1) + "\n[source abcdef123456 (code) L1-L1]"
        first = generator._sliced_context("what does the code do?", big_context)
        second = generator._sliced_context("what does the code do?", big_context)
        other = generator._sliced_context("what do the metrics say?", big_context)
    assert first == second  # identical prefix for every persona on this question
    assert provider.calls["sidekick/context_query"] == 2  # one per distinct question
    assert other


def test_truncated_retrieval_uses_partial_spans_not_full_corpus(tmp_path, monkeypatch) -> None:
    from bokken.journal.store import JournalStore
    from bokken.models import ModelRouter
    from bokken.models.router import ProviderResult
    from bokken.orchestrator import create_session
    from bokken.stages.persona_gen import DELEGATE_THRESHOLD_CHARS, RouterTurnGenerator

    class TruncatingProvider:
        def complete(self, **kw):
            return ProviderResult(
                text="[source abcdef123456 (code) L1-L1] partial span",
                data=None,
                usage={"input_tokens": 10, "output_tokens": 8000},
                request_id="trunc-1",
                stop_reason="max_tokens",
                model=kw["model"],
            )

    session_dir = create_session("trunc-unit", brief=BRIEF, mode="dojo", gate_policy="none")
    with JournalStore.open(session_dir) as store:
        generator = RouterTurnGenerator(ModelRouter(store, TruncatingProvider()))
        big = "x" * (DELEGATE_THRESHOLD_CHARS + 1)
        sliced = generator._sliced_context("q?", big)
    assert sliced == "[source abcdef123456 (code) L1-L1] partial span"


def test_wireframe_artifact_generated_on_tokens_and_exercised(tmp_path, monkeypatch) -> None:
    from bokken.journal import read_events
    from bokken.orchestrator import create_session
    from bokken.stages import walkthrough as wt2

    monkeypatch.setattr(wt2, "build_walker", lambda: FakeWalker2())
    inputs = make_inputs(tmp_path)
    css = tmp_path / "styles.css"
    css.write_text(":root{--accent:#c00}.card{border:1px solid}")
    inputs["repo"] = str(tmp_path)  # repo with css tokens
    session_dir = create_session(
        "wireframe-e2e",
        brief={**BRIEF, "inputs": inputs},
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    provider = WireframeProvider()
    assert make_runner(session_dir, provider).run().halt == "completed"
    events = list(read_events(session_dir))
    wf = next(e for e in events if e.payload.get("kind") == "wireframe_html")
    path = session_dir / wf.payload["path"]
    assert path.suffix == ".html" and "<h1>Mock</h1>" in path.read_text()
    exercised = [
        e
        for e in events
        if e.type == "evidence.captured" and e.payload.get("source") == "wireframe_exercise"
    ]
    assert exercised and exercised[0].payload["confidence_class"] == "observed"


class FakeWalker2:
    def visit(self, app_url, *, max_pages=12, seed_paths=None):
        import base64

        from bokken.stages import walkthrough as wt3

        return [
            wt3.PageObservation(
                url=app_url,
                title="Mock",
                load_ms=5,
                screenshot_png=base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
                    "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
                ),
            )
        ]


class WireframeProvider(ScriptedProvider):
    def _dispatch(self, prompt_id, rendered):
        from bokken.stages import schemas as s2

        if prompt_id == "prototype/fidelity":
            return s2.FidelityChoice(
                artifacts=[s2.ArtifactPlanItem(kind="wireframe_html", assumption_indexes=[0])],
                rationale="a screen mock is the cheapest test of comprehension",
            )
        return super()._dispatch(prompt_id, rendered)
