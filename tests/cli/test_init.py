"""Tests for `bokken init` (issue #27): templates in, valid brief out."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from bokken.cli.app import app
from bokken.cli.templates import TEMPLATES, build_brief
from bokken.journal.schema import Brief

runner = CliRunner()


def test_every_template_builds_a_valid_brief():
    for name in TEMPLATES:
        Brief.model_validate(build_brief(name, "Acme"))


def test_non_interactive_template_writes_brief_and_next_commands(tmp_path):
    out = tmp_path / "brief.json"
    result = runner.invoke(app, ["init", "--template", "saas-retention", "--out", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    Brief.model_validate(data)
    assert "TODO" in data["problem_space"]
    flat = result.output.replace("\n", "")
    assert "bokken new brief --brief" in flat
    assert "bokken run brief" in flat


def test_unknown_template_is_rejected(tmp_path):
    result = runner.invoke(
        app, ["init", "--template", "nope", "--out", str(tmp_path / "b.json")]
    )
    assert result.exit_code != 0
    assert not (tmp_path / "b.json").exists()


def test_interactive_path_prefills_from_template(tmp_path):
    out = tmp_path / "acme-brief.json"
    answers = "\n".join(["1", "Acme", "", "", "", ""]) + "\n"
    result = runner.invoke(app, ["init", "--out", str(out)], input=answers)
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert "Acme" in data["problem_space"]  # sorted order: 1 = consumer-app
    assert data["target_segments"] == TEMPLATES["consumer-app"]["target_segments"]
    assert "bokken new acme --brief" in result.output.replace("\n", "")
