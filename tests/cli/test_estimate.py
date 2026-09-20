"""`bokken estimate <brief.json>` predicts cost + tokens before a session exists:
derivation only, a low-high range, a lane breakdown, a stable `--json` shape, and
a clean exit-2 refusal for an unreadable or schema-invalid brief."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bokken.cli.app import app
from bokken.contract import EstimateResult
from tests.stages.test_engines_e2e import BRIEF

runner = CliRunner()


def _brief(tmp_path: Path) -> Path:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    return path


def test_json_is_one_estimate_document_stderr_empty_exit_zero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["estimate", str(_brief(tmp_path)), "--panel-size", "6", "--json"])
    assert result.exit_code == 0
    assert result.stderr == ""
    parsed = EstimateResult.model_validate_json(result.stdout)
    assert parsed.kind == "estimate"
    assert parsed.panel_size == 6
    assert parsed.cost_low_usd <= parsed.cost_high_usd
    assert round(sum(la.cost_usd for la in parsed.lanes), 4) == parsed.cost_point_usd
    assert [la.lane for la in parsed.lanes] == ["exploration", "research", "synthesis"]


def test_no_session_or_journal_is_written(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("BOKKEN_HOME", str(home))
    result = runner.invoke(app, ["estimate", str(_brief(tmp_path)), "--json"])
    assert result.exit_code == 0
    # Pure derivation: nothing landed in the workspace.
    assert not home.exists() or not any(home.rglob("journal.jsonl"))


def test_estimate_scales_with_panel_size(tmp_path: Path) -> None:
    brief = _brief(tmp_path)
    small = EstimateResult.model_validate_json(
        runner.invoke(app, ["estimate", str(brief), "--panel-size", "4", "--json"]).stdout
    )
    large = EstimateResult.model_validate_json(
        runner.invoke(app, ["estimate", str(brief), "--panel-size", "10", "--json"]).stdout
    )
    assert large.cost_point_usd > small.cost_point_usd
    lane = {e.panel_size: {la.lane: la for la in e.lanes} for e in (small, large)}
    assert lane[10]["research"].calls > lane[4]["research"].calls


def test_provider_and_model_change_the_priced_estimate(tmp_path: Path) -> None:
    brief = _brief(tmp_path)
    default = EstimateResult.model_validate_json(
        runner.invoke(app, ["estimate", str(brief), "--json"]).stdout
    )
    openai = EstimateResult.model_validate_json(
        runner.invoke(app, ["estimate", str(brief), "--provider", "openai", "--json"]).stdout
    )
    override = EstimateResult.model_validate_json(
        runner.invoke(app, ["estimate", str(brief), "--model", "claude-opus-4-8", "--json"]).stdout
    )
    assert openai.cost_point_usd != default.cost_point_usd
    assert override.cost_point_usd != default.cost_point_usd


def test_human_output_is_labeled_modeled_and_points_to_costs(tmp_path: Path) -> None:
    result = runner.invoke(app, ["estimate", str(_brief(tmp_path))])
    assert result.exit_code == 0
    text = result.stdout.lower()
    assert "modeled estimate" in text
    assert "not a measurement" in text
    assert "bokken costs" in text


def test_missing_brief_exits_2_to_stderr(tmp_path: Path) -> None:
    result = runner.invoke(app, ["estimate", str(tmp_path / "does-not-exist.json")])
    assert result.exit_code == 2
    assert "does-not-exist.json" in result.stderr


def test_schema_invalid_brief_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"target_segments": ["x"]}))  # missing problem_space etc.
    result = runner.invoke(app, ["estimate", str(bad)])
    assert result.exit_code == 2
