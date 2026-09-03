"""bokken doctor: facts with fixes, secrets never printed (issue #48)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from bokken.cli.app import app

runner = CliRunner()


def test_doctor_reports_key_presence_without_values(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-value")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "sk-ant-secret-value" not in result.output
    flat = result.output.replace("\n", "")
    assert "ANTHROPIC_API_KEY" in flat and "present" in flat


def test_doctor_json_contract(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.stdout)
    assert isinstance(payload["ok"], bool)
    names = {c["name"] for c in payload["checks"]}
    assert {"bokken", "workspace", "ANTHROPIC_API_KEY"} <= names
    missing = next(c for c in payload["checks"] if c["name"] == "ANTHROPIC_API_KEY")
    assert missing["ok"] is False and missing["fix"]
