import json
import re
from pathlib import Path

import pytest

from bokken.dossier import DOJO_BANNER, build_model, generate
from bokken.journal import read_events
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, FounderPort, make_inputs, make_runner


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


@pytest.fixture
def dojo_session(tmp_path: Path) -> Path:
    from bokken.orchestrator import create_session

    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    session_dir = create_session(
        "dossier-dojo",
        brief=brief,
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    assert make_runner(session_dir, ScriptedProvider()).run().halt == "completed"
    return session_dir


def strip_timestamp(text: str) -> str:
    return re.sub(r"\d{4}-\d{2}-\d{2}T[\d:+-]+", "TS", text)


def test_generation_is_deterministic_and_makes_no_model_calls(dojo_session: Path) -> None:
    calls_before = sum(1 for e in read_events(dojo_session) if e.type == "model.called")
    md1, json1, status = generate(dojo_session)
    first_md, first_json = md1.read_text(), json1.read_text()
    md2, json2, _ = generate(dojo_session)
    assert status == "complete"
    assert strip_timestamp(first_md) == strip_timestamp(md2.read_text())
    assert strip_timestamp(first_json) == strip_timestamp(json2.read_text())
    calls_after = sum(1 for e in read_events(dojo_session) if e.type == "model.called")
    assert calls_after == calls_before


def test_exports_are_journaled_as_artifacts(dojo_session: Path) -> None:
    generate(dojo_session)
    kinds = [e.payload["kind"] for e in read_events(dojo_session) if e.type == "artifact.generated"]
    assert "dossier_markdown" in kinds and "dossier_json" in kinds


def test_part_a_claims_have_receipts_resolvable_in_part_c(dojo_session: Path) -> None:
    md_path, json_path, _ = generate(dojo_session)
    document = json.loads(json_path.read_text())
    markdown = md_path.read_text()
    recommendation = document["recommendation"]
    assert recommendation is not None
    assert f"decision `{recommendation['id']}`" in markdown
    assert recommendation["id"] in document["decisions"]
    model = build_model(dojo_session)
    for insight in model.insights.values():
        for ref in insight.evidence_ids:
            assert model.resolves(ref)
    for artifact in model.artifacts:
        for ref in artifact.assumption_ids:
            assert model.resolves(ref)


def test_dojo_banner_and_synthetic_labeling(dojo_session: Path) -> None:
    md_path, json_path, _ = generate(dojo_session)
    markdown = md_path.read_text()
    assert markdown.startswith(f"# Session Dossier - dossier-dojo\n\n{DOJO_BANNER}")
    assert "[requires real validation]" in markdown
    document = json.loads(json_path.read_text())
    assert all(
        e["synthetic"] == (e["confidence_class"] == "simulated")
        for e in document["evidence"].values()
    )
    assert any(e["synthetic"] for e in document["evidence"].values())


def test_negative_space_lists_debt_and_suppressions(dojo_session: Path) -> None:
    md_path, _, _ = generate(dojo_session)
    markdown = md_path.read_text()
    assert "What this run did not do" in markdown
    model = build_model(dojo_session)
    for debt in model.negative_space.research_debt:
        assert debt.question in markdown


def test_partial_dossier_for_in_flight_session(tmp_path: Path) -> None:
    from bokken.orchestrator import create_session

    session_dir = create_session("dossier-partial", brief=BRIEF, mode="founder")
    runner = make_runner(session_dir, ScriptedProvider(), input_port=FounderPort())
    runner.step()  # intake -> empathize only
    md_path, json_path, status = generate(session_dir)
    assert status == "partial"
    markdown = md_path.read_text()
    assert "Status: partial" in markdown
    assert "not yet selected" in markdown
    document = json.loads(json_path.read_text())
    assert "prototype" in document["negative_space"]["stages_not_reached"]


def test_persona_provenance_cards_present(dojo_session: Path) -> None:
    _, json_path, _ = generate(dojo_session)
    document = json.loads(json_path.read_text())
    kinds = {card["panel_kind"] for card in document["personas"]}
    assert kinds == {"interview", "ideation", "test"}
    assert all(card["persona_id"] for card in document["personas"])


def test_synthetic_propagates_through_interpretation_refs() -> None:
    """An opportunity refs an outcome_score which refs a desired_outcome grounded
    only in simulated evidence: every link of that chain is synthetic, including
    the ones whose refs never point at evidence directly (the honesty rule says
    confidence classes propagate to everything derived from them)."""
    from bokken.journal import Actor, JournalStore
    from bokken.orchestrator import create_session

    session_dir = create_session("dossier-honesty", brief=BRIEF, mode="dojo")
    facilitator = Actor(kind="agent", name="facilitator")
    persona = Actor(kind="agent", name="Marta", persona_id="p-1")
    with JournalStore.open(session_dir) as store:
        ev = store.append(
            type="evidence.captured",
            stage="empathize",
            actor=persona,
            payload={
                "content": "arrival predictions are wrong",
                "source": "panel interview",
                "confidence_class": "simulated",
                "speaker": "Marta",
            },
        )
        outcome = store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=facilitator,
            payload={"kind": "desired_outcome", "statement": "know the real arrival time"},
            refs=[ev.id],
        )
        score = store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=persona,
            payload={
                "kind": "outcome_score",
                "statement": "Marta scores outcome 0: importance 9, satisfaction 2",
                "importance": 9,
                "satisfaction": 2,
                "persona_id": "p-1",
            },
            refs=[outcome.id],
        )
        opportunity = store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=facilitator,
            payload={
                "kind": "opportunity",
                "statement": (
                    "O0: know the real arrival time - opportunity 16.0 (severely underserved)"
                ),
                "score": 16.0,
                "band": "severely underserved",
            },
            refs=[outcome.id, score.id],
        )
    model = build_model(session_dir)
    assert model.insights[outcome.id].synthetic is True
    assert model.insights[score.id].synthetic is True  # refs only another interpretation
    assert model.insights[opportunity.id].synthetic is True
    assert model.insights[opportunity.id].score == 16.0
    assert model.insights[opportunity.id].band == "severely underserved"


def test_markdown_flattens_injected_journal_text() -> None:
    """Journal free text is interpolated into dossier.md: an embedded newline +
    "## " must render as one flat line, never as a real markdown heading."""
    from bokken.dossier import render_markdown
    from bokken.journal import Actor, JournalStore
    from bokken.orchestrator import create_session

    session_dir = create_session("dossier-inject", brief=BRIEF, mode="founder")
    injected = "line one\n## Fake heading\nline two"
    with JournalStore.open(session_dir) as store:
        store.append(
            type="decision.recorded",
            stage="define",
            actor=Actor(kind="agent", name="facilitator"),
            payload={
                "question": f"problem statement: {injected}",
                "options": [injected],
                "criteria": ["evidence"],
                "resolution": injected,
                "dissent": [{"actor": "skeptic", "reservation": injected}],
            },
        )
        store.append(
            type="assumption.registered",
            stage="prototype",
            actor=Actor(kind="agent", name="facilitator"),
            payload={"statement": injected, "impact": "high", "uncertainty": "high"},
        )
    markdown = render_markdown(build_model(session_dir), "TS")
    assert "\n## Fake heading" not in markdown
    assert "line one ## Fake heading line two" in markdown


def test_prototype_artifacts_hide_bookkeeping_and_empty_assumption_clause() -> None:
    from bokken.journal import Actor, JournalStore
    from bokken.orchestrator import create_session

    session_dir = create_session("dossier-artifacts", brief=BRIEF, mode="founder")
    facilitator = Actor(kind="agent", name="facilitator")
    with JournalStore.open(session_dir) as store:
        assumption = store.append(
            type="assumption.registered",
            stage="prototype",
            actor=facilitator,
            payload={"statement": "riders will pre-book", "impact": "high", "uncertainty": "high"},
        )
        store.append(
            type="artifact.generated",
            stage="prototype",
            actor=facilitator,
            payload={
                "path": "artifacts/prototype/landing.md",
                "kind": "landing_page",
                "content_hash": "a" * 64,
            },
            refs=[assumption.id],
        )
        store.append(
            type="artifact.generated",
            stage="prototype",
            actor=facilitator,
            payload={
                "path": "artifacts/prototype/notes.md",
                "kind": "notes",
                "content_hash": "b" * 64,
            },
        )
        store.append(  # bookkeeping: must not appear under "Prototype artifacts"
            type="artifact.generated",
            stage="empathize",
            actor=facilitator,
            payload={
                "path": "artifacts/empathize/opportunity_ranking.md",
                "kind": "opportunity_ranking",
                "content_hash": "c" * 64,
            },
        )
    from bokken.dossier import render_markdown

    markdown = render_markdown(build_model(session_dir), "TS")
    assert f"tests assumptions: `{assumption.id}`" in markdown
    assert f"- `artifacts/prototype/notes.md` (notes, sha256 `{'b' * 12}`)\n" in markdown
    assert "opportunity_ranking" not in markdown


def test_truncated_panel_manifest_degrades_instead_of_crashing() -> None:
    """A bad manifest file is replayed on every future dossier/report build, so
    it must degrade the persona list instead of failing those builds forever."""
    from bokken.journal import Actor, JournalStore
    from bokken.orchestrator import create_session

    session_dir = create_session("dossier-manifest", brief=BRIEF, mode="dojo")
    truncated = session_dir / "artifacts" / "empathize" / "panel.json"
    truncated.parent.mkdir(parents=True)
    truncated.write_text('{"panel_kind": "interview", "personas": [{"persona_id"', encoding="utf-8")
    keyless = session_dir / "artifacts" / "empathize" / "panel2.json"
    keyless.write_text('{"personas": [{"name": "Marta"}]}', encoding="utf-8")
    with JournalStore.open(session_dir) as store:
        for path in ("artifacts/empathize/panel.json", "artifacts/empathize/panel2.json"):
            store.append(
                type="artifact.generated",
                stage="empathize",
                actor=Actor(kind="agent", name="facilitator"),
                payload={"path": path, "kind": "panel_manifest", "content_hash": "d" * 64},
            )
    model = build_model(session_dir)  # must not raise
    assert model.personas == []
