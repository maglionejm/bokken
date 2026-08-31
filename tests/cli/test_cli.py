import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bokken.cli import wiring
from bokken.cli.app import app
from bokken.models import ModelRouter
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF

runner = CliRunner()


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        wiring, "router_factory", lambda: lambda store: ModelRouter(store, ScriptedProvider())
    )
    return tmp_path


@pytest.fixture
def brief_file(tmp_path: Path) -> Path:
    from tests.stages.test_engines_e2e import make_inputs

    path = tmp_path / "brief.json"
    path.write_text(json.dumps({**BRIEF, "inputs": make_inputs(tmp_path)}))
    return path


def new_session(brief_file: Path, name: str = "s1", *extra: str):
    return runner.invoke(app, ["new", name, "--brief", str(brief_file), "--mode", "dojo", *extra])


def test_new_and_status_machine_output(brief_file: Path) -> None:
    created = new_session(brief_file, "mars-lander", "--json")
    assert created.exit_code == 0, created.output
    result = runner.invoke(app, ["status", "mars-lander", "--json"])
    assert result.exit_code == 0
    document = json.loads(result.stdout)
    assert document["stage"] == "intake"
    assert document["mode"] == "dojo"
    assert result.stderr == ""


def test_unknown_session_exits_2_naming_workspace() -> None:
    result = runner.invoke(app, ["status", "ghost"])
    assert result.exit_code == 2
    assert "ghost" in result.stderr and "sessions" in result.stderr


def test_duplicate_name_exits_2(brief_file: Path) -> None:
    assert new_session(brief_file).exit_code == 0
    result = new_session(brief_file)
    assert result.exit_code == 2
    assert "already exists" in result.stderr


def test_run_halts_at_gate_then_resumes_to_completion(brief_file: Path) -> None:
    new_session(brief_file, "dojo-run")
    result = runner.invoke(app, ["run", "dojo-run", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["halt"] == "gate_pending"

    status = runner.invoke(app, ["status", "dojo-run", "--json"])
    gate = json.loads(status.stdout)["pending_gate"]
    assert gate["from_stage"] == "intake"

    while True:
        outcome = json.loads(runner.invoke(app, ["run", "dojo-run", "--json"]).stdout)
        if outcome["halt"] == "completed":
            break
        assert outcome["halt"] == "gate_pending"
        approved = runner.invoke(app, ["gate", "dojo-run", "approve"])
        assert approved.exit_code == 0
    final = json.loads(runner.invoke(app, ["status", "dojo-run", "--json"]).stdout)
    assert final["stage"] == "complete"


def test_gate_reject_requires_reason(brief_file: Path) -> None:
    new_session(brief_file, "g1")
    runner.invoke(app, ["run", "g1", "--json"])
    result = runner.invoke(app, ["gate", "g1", "reject"])
    assert result.exit_code == 2 and "--reason" in result.stderr
    result = runner.invoke(app, ["gate", "g1", "reject", "--reason", "brief too vague"])
    assert result.exit_code == 0


def test_illegal_loopback_exits_2_naming_legal_edges(brief_file: Path) -> None:
    new_session(brief_file, "lb", "--gates", "none")
    runner.invoke(app, ["step", "lb", "--json"])  # -> empathize
    result = runner.invoke(app, ["back", "lb", "prototype", "--reason", "nope"])
    assert result.exit_code == 2
    assert "legal targets" in result.stderr


def test_journal_since_accepts_seq_and_timestamp(brief_file: Path) -> None:
    new_session(brief_file, "since1", "--gates", "none")
    runner.invoke(app, ["run", "since1", "--json"])
    by_seq = runner.invoke(app, ["journal", "since1", "--since", "5", "--json"])
    lines = [json.loads(line) for line in by_seq.stdout.strip().splitlines()]
    assert lines and all(line["seq"] >= 5 for line in lines)

    pivot_ts = lines[0]["ts"]
    by_ts = runner.invoke(app, ["journal", "since1", "--since", pivot_ts, "--json"])
    ts_lines = [json.loads(line) for line in by_ts.stdout.strip().splitlines()]
    assert ts_lines and all(line["ts"] >= pivot_ts for line in ts_lines)

    bad = runner.invoke(app, ["journal", "since1", "--since", "yesterday-ish"])
    assert bad.exit_code == 2 and "ISO timestamp" in bad.stderr


def test_journal_filters_and_jsonl(brief_file: Path) -> None:
    new_session(brief_file, "j1", "--gates", "none")
    run = runner.invoke(app, ["run", "j1", "--json"])
    assert json.loads(run.stdout)["halt"] == "completed"
    result = runner.invoke(
        app, ["journal", "j1", "--type", "option", "--stage", "ideate", "--json"]
    )
    assert result.exit_code == 0
    lines = [json.loads(line) for line in result.stdout.strip().splitlines()]
    assert lines and all(line["type"].startswith("option.") for line in lines)
    assert [line["seq"] for line in lines] == sorted(line["seq"] for line in lines)


def test_dossier_partial_status(brief_file: Path) -> None:
    new_session(brief_file, "d1", "--gates", "none")
    runner.invoke(app, ["step", "d1", "--json"])
    result = runner.invoke(app, ["dossier", "d1", "--json"])
    assert result.exit_code == 0
    document = json.loads(result.stdout)
    assert document["status"] == "partial"
    assert Path(document["markdown_path"]).exists()


def test_list_and_stop(brief_file: Path) -> None:
    new_session(brief_file, "l1")
    result = runner.invoke(app, ["list", "--json"])
    assert json.loads(result.stdout)["sessions"][0]["slug"] == "l1"
    assert runner.invoke(app, ["stop", "l1", "--reason", "lunch"]).exit_code == 0
    status = json.loads(runner.invoke(app, ["status", "l1", "--json"]).stdout)
    assert status["state"] == "stopped"


def test_help_lists_all_verbs() -> None:
    result = runner.invoke(app, ["--help"])
    for verb in (
        "new",
        "run",
        "step",
        "stop",
        "status",
        "list",
        "gate",
        "back",
        "journal",
        "dossier",
    ):
        assert verb in result.stdout
