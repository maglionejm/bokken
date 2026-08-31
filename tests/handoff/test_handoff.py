import json
from pathlib import Path

import pytest

from bokken.handoff import (
    HandoffRefusedError,
    finalize_session,
    generate_handoff,
    handoff_exists,
    validate_package,
)
from bokken.handoff.render import ensure_shall, kebab
from bokken.journal import Actor, read_events
from bokken.models import ModelRouter
from bokken.orchestrator import create_session
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs, make_runner

AGENT = Actor(kind="agent", name="facilitator", model="fake")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def router_factory():
    return lambda store: ModelRouter(store, ScriptedProvider())


@pytest.fixture
def completed_session(tmp_path: Path) -> Path:
    brief = {**BRIEF, "inputs": make_inputs(tmp_path)}
    session_dir = create_session(
        "handoff-dojo",
        brief=brief,
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    assert make_runner(session_dir, ScriptedProvider()).run().halt == "completed"
    return session_dir


def read_package(session_dir: Path) -> dict[str, str]:
    root = session_dir / "handoff"
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file()
    }


def test_package_generation_and_format(completed_session: Path) -> None:
    result = generate_handoff(completed_session, router_factory())
    assert result["change_id"] == "handoff-dojo"[:0] + "build-mvp-handoff-dojo"
    assert result["capabilities"] == ["schedule-publication"]

    files = read_package(completed_session)
    change = "openspec/changes/build-mvp-handoff-dojo"
    for expected in (
        "README.md",
        "traceability.json",
        f"{change}/proposal.md",
        f"{change}/design.md",
        f"{change}/tasks.md",
        f"{change}/specs/schedule-publication/spec.md",
    ):
        assert expected in files, expected
    assert validate_package(files) == []

    spec = files[f"{change}/specs/schedule-publication/spec.md"]
    assert "## ADDED Requirements" in spec
    assert "The system SHALL operators can publish"[:20] in spec  # normalized SHALL
    assert "#### Scenario:" in spec  # scaffolded scenario

    events = list(read_events(completed_session))
    kinds = [e.payload.get("kind") for e in events if e.type == "artifact.generated"]
    assert kinds.count("handoff_package") == 1
    assert kinds.count("handoff_spec") == len(files)


def test_traceability_resolves_to_ledger(completed_session: Path) -> None:
    generate_handoff(completed_session, router_factory())
    trace = json.loads((completed_session / "handoff" / "traceability.json").read_text())
    event_ids = {e.id for e in read_events(completed_session)}
    for ref in trace["ledger_refs"].values():
        assert ref is None or ref in event_ids
    for capability in trace["capabilities"].values():
        for requirement in capability.values():
            for assumption_id in requirement["assumption_ids"]:
                assert assumption_id in event_ids


def test_contradicted_assumption_is_excluded(completed_session: Path) -> None:
    generate_handoff(completed_session, router_factory())
    files = read_package(completed_session)
    change = "openspec/changes/build-mvp-handoff-dojo"
    spec = files[f"{change}/specs/schedule-publication/spec.md"]
    assert "Detour-based rerouting" not in spec  # rested on the contradicted assumption
    design = files[f"{change}/design.md"]
    assert "Do NOT build on" in design
    assert "detours" in design


def test_validation_debt_becomes_mandatory_tasks(completed_session: Path) -> None:
    generate_handoff(completed_session, router_factory())
    files = read_package(completed_session)
    tasks = files["openspec/changes/build-mvp-handoff-dojo/tasks.md"]
    assert "Real-world validation (mandatory)" in tasks
    assert "requires_real_validation" in tasks or "untested" in tasks
    readme = files["README.md"]
    assert "SIMULATED VALIDATION" in readme  # dojo banner


def test_refusals(tmp_path: Path) -> None:
    from bokken.journal import JournalStore

    # No convergence decision.
    bare = create_session("bare", brief=BRIEF, mode="founder")
    with pytest.raises(HandoffRefusedError, match="convergence"):
        generate_handoff(bare, router_factory())

    # Kill recommendation.
    killed = create_session("killed", brief=BRIEF, mode="founder")
    with JournalStore.open(killed) as store:
        option = store.append(
            type="option.created", stage="ideate", actor=AGENT, payload={"summary": "x"}
        )
        store.append(
            type="decision.recorded",
            stage="ideate",
            actor=AGENT,
            payload={
                "question": "which concept advances",
                "options": [option.id],
                "criteria": ["dfv"],
                "resolution": "x",
                "dissent": [],
            },
        )
        store.append(
            type="decision.recorded",
            stage="test",
            actor=AGENT,
            payload={
                "question": "kill, iterate, or proceed",
                "options": ["kill", "iterate", "proceed"],
                "criteria": ["scores"],
                "resolution": "kill",
                "dissent": [],
            },
        )
    with pytest.raises(HandoffRefusedError, match="kill"):
        generate_handoff(killed, router_factory())
    assert not (killed / "handoff").exists()


def test_finalize_generates_both_then_is_idempotent(completed_session: Path) -> None:
    first = finalize_session(completed_session, router_factory())
    assert first.dossier_generated and first.handoff_generated
    assert (completed_session / "dossier" / "dossier.md").exists()
    assert handoff_exists(completed_session)
    events_after_first = len(list(read_events(completed_session)))

    second = finalize_session(completed_session, router_factory())
    assert not second.dossier_generated and not second.handoff_generated
    assert len(list(read_events(completed_session))) == events_after_first


def test_normalization_helpers() -> None:
    assert kebab("Schedule Publication") == "schedule-publication"
    assert ensure_shall("operators publish schedules").startswith("The system SHALL ")
    assert ensure_shall("The app SHALL work.") == "The app SHALL work."
