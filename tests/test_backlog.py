"""Tests for the validation backlog: ranked, exportable, replay-derived, no model call.

Sessions are built by appending journal events directly (the backlog is pure
derivation from the journal), then exercised through both the helper and the CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bokken.backlog import build_backlog, to_csv, to_markdown
from bokken.cli.app import app
from bokken.journal import Actor, read_events
from bokken.journal.store import JournalStore
from bokken.orchestrator import create_session

runner = CliRunner()

BRIEF = {
    "problem_space": "fleet operators struggle to fill idle vehicles",
    "target_segments": ["fleet operators"],
    "success_criteria": ["operators adopt pre-booking"],
    "risk_tolerance": "medium",
}
FACILITATOR = Actor(kind="agent", name="facilitator")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


def _register(store: JournalStore, statement: str, impact: str, uncertainty: str) -> str:
    return store.append(
        type="assumption.registered",
        stage="prototype",
        actor=FACILITATOR,
        payload={"statement": statement, "impact": impact, "uncertainty": uncertainty},
    ).id


def _score(
    store: JournalStore,
    assumption_id: str,
    score: str,
    *,
    confidence_class: str = "simulated",
    speaker: str | None = "Persona",
) -> None:
    payload = {
        "content": f"reaction to {assumption_id}",
        "source": "persona:p1" if speaker else "founder read-through",
        "confidence_class": confidence_class,
    }
    if speaker:
        payload["speaker"] = speaker
    reaction = store.append(
        type="evidence.captured", stage="test", actor=FACILITATOR, payload=payload
    )
    store.append(
        type="assumption.scored",
        stage="test",
        actor=FACILITATOR,
        payload={"score": score},
        refs=[assumption_id, reaction.id],
    )


def _abstain(store: JournalStore, question: str, gap: str) -> str:
    return store.append(
        type="evidence.abstained",
        stage="empathize",
        actor=FACILITATOR,
        payload={"question": question, "gap": gap},
    ).id


def _dojo_session_with_register(name: str = "mars-lander") -> Path:
    """A dojo session: untested + contradicted assumptions, one supported, research debt."""
    session_dir = create_session(name, brief=BRIEF, mode="dojo", gate_policy="none")
    with JournalStore.open(session_dir) as store:
        high = _register(store, "riders will pre-book", "high", "high")  # untested, priority 9
        med = _register(store, "drivers accept surge", "medium", "medium")  # untested, priority 4
        contra = _register(store, "market wants this", "high", "medium")  # contradicted, priority 6
        supp = _register(store, "payments are simple", "low", "low")  # supported -> excluded
        _score(store, high, "untested")
        _score(store, med, "untested")
        _score(store, contra, "contradicted")
        _score(store, supp, "supported")
        _abstain(store, "How large is the fleet market?", "no market sizing sources in corpus")
    return session_dir


def test_ranked_by_impact_times_uncertainty_and_supported_excluded() -> None:
    session_dir = _dojo_session_with_register()
    result = build_backlog(session_dir, "mars-lander")

    assumptions = [it for it in result.items if it.kind == "assumption"]
    priorities = [it.priority for it in assumptions]
    assert priorities == sorted(priorities, reverse=True)  # highest first
    # 9 (untested high/high), 6 (contradicted high/med), 4 (untested med/med).
    assert priorities == [9, 6, 4]
    # Supported assumption is counted but never listed.
    assert all("payments are simple" not in it.statement for it in result.items)
    assert result.supported == 1
    assert result.contradicted == 1
    assert result.untested == 2


def test_research_debt_is_included_as_items() -> None:
    session_dir = _dojo_session_with_register()
    result = build_backlog(session_dir, "mars-lander")
    debt = [it for it in result.items if it.kind == "research_debt"]
    assert len(debt) == 1
    assert result.research_debt == 1
    assert "fleet market" in debt[0].statement
    # Research debt lands after the ranked assumptions.
    assert result.items[-1].kind == "research_debt"
    # Ranks are contiguous from 1.
    assert [it.rank for it in result.items] == list(range(1, len(result.items) + 1))


def test_flip_the_verdict_states_counts_not_a_threshold() -> None:
    session_dir = _dojo_session_with_register()
    result = build_backlog(session_dir, "mars-lander")
    line = result.flip_the_verdict
    assert "1 supported" in line and "1 contradicted" in line and "2 untested" in line
    assert "2 untested" in line and "would have to resolve" in line
    assert "standing" in line and "kill-or-iterate" in line
    # No invented cutoff phrasing.
    assert "threshold" not in line.lower()


def test_empty_backlog_when_all_supported_and_no_debt() -> None:
    session_dir = create_session("mars-lander", brief=BRIEF, mode="founder", gate_policy="none")
    with JournalStore.open(session_dir) as store:
        a = _register(store, "payments are simple", "low", "low")
        _score(store, a, "supported", confidence_class="observed", speaker=None)
    result = build_backlog(session_dir, "mars-lander")
    assert result.items == []
    assert result.supported == 1
    assert result.research_debt == 0
    assert "Nothing left to test" in result.flip_the_verdict


def test_simulated_only_backlog_keeps_simulated_framing() -> None:
    session_dir = _dojo_session_with_register()
    result = build_backlog(session_dir, "mars-lander")
    assert result.simulated_only is True
    assert result.dojo_banner is True
    assert result.requires_real_validation is True
    assert result.banner is not None and "SIMULATED RUN" in result.banner
    assert all(it.confidence_class == "simulated" for it in result.items)


def test_founder_observed_scores_do_not_read_as_simulated() -> None:
    session_dir = create_session("mars-lander", brief=BRIEF, mode="founder", gate_policy="none")
    with JournalStore.open(session_dir) as store:
        a = _register(store, "riders will pre-book", "high", "high")
        _score(store, a, "contradicted", confidence_class="observed", speaker=None)
    result = build_backlog(session_dir, "mars-lander")
    assert result.items[0].confidence_class == "observed"
    assert result.simulated_only is False
    assert result.requires_real_validation is False


def test_no_model_calls_and_deterministic() -> None:
    session_dir = _dojo_session_with_register()
    calls = sum(1 for e in read_events(session_dir) if e.type == "model.called")
    first = build_backlog(session_dir, "mars-lander").model_dump_json()
    second = build_backlog(session_dir, "mars-lander").model_dump_json()
    assert first == second
    # Building the backlog appends nothing and calls no model.
    assert calls == 0
    assert sum(1 for e in read_events(session_dir) if e.type == "model.called") == 0


def test_csv_and_markdown_export_the_same_ranked_items() -> None:
    session_dir = _dojo_session_with_register()
    result = build_backlog(session_dir, "mars-lander")

    csv_text = to_csv(result)
    lines = [ln for ln in csv_text.splitlines() if ln]
    assert lines[0].startswith(
        "rank,kind,impact,uncertainty,score,confidence_class,source,statement"
    )
    assert len(lines) == 1 + len(result.items)  # header + one row per item

    md_text = to_markdown(result)
    checkboxes = [ln for ln in md_text.splitlines() if ln.startswith("- [ ]")]
    assert len(checkboxes) == len(result.items)
    assert md_text.startswith("# Validation backlog - mars-lander")
    assert "SIMULATED RUN" in md_text  # banner restated in the export


# --- CLI surface -----------------------------------------------------------


def test_cli_table_json_csv_markdown_parity() -> None:
    _dojo_session_with_register()

    table = runner.invoke(app, ["backlog", "mars-lander"])
    assert table.exit_code == 0, table.output
    assert "Validation backlog" in table.stdout
    assert "what" not in table.stdout.lower() or "flip" in table.stdout.lower()

    doc = runner.invoke(app, ["backlog", "mars-lander", "--json"])
    assert doc.exit_code == 0
    payload = json.loads(doc.stdout)
    assert payload["kind"] == "backlog"
    assert payload["supported"] == 1 and payload["untested"] == 2
    assert payload["simulated_only"] is True
    assert len(payload["items"]) == 4  # 3 assumptions + 1 research debt

    csv_out = runner.invoke(app, ["backlog", "mars-lander", "--format", "csv"])
    assert csv_out.exit_code == 0
    assert csv_out.stdout.splitlines()[0].startswith("rank,kind,impact")

    md_out = runner.invoke(app, ["backlog", "mars-lander", "--format", "markdown"])
    assert md_out.exit_code == 0
    assert md_out.stdout.startswith("# Validation backlog - mars-lander")


def test_cli_unknown_session_exits_2() -> None:
    result = runner.invoke(app, ["backlog", "ghost"])
    assert result.exit_code == 2
    assert "ghost" in result.stderr


def test_cli_bad_format_exits_2() -> None:
    _dojo_session_with_register()
    result = runner.invoke(app, ["backlog", "mars-lander", "--format", "pdf"])
    assert result.exit_code == 2
    assert "csv" in result.stderr and "markdown" in result.stderr


def test_cli_empty_backlog_exits_0() -> None:
    session_dir = create_session("all-good", brief=BRIEF, mode="founder", gate_policy="none")
    with JournalStore.open(session_dir) as store:
        a = _register(store, "payments are simple", "low", "low")
        _score(store, a, "supported", confidence_class="observed", speaker=None)
    result = runner.invoke(app, ["backlog", "all-good", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["items"] == []
    assert "Nothing left to test" in payload["flip_the_verdict"]
