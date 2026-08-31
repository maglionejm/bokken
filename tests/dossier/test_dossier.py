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
