"""Report themes: chrome changes, content never does (issue #48)."""

from __future__ import annotations

import json

import pytest

from bokken.report.theme import Theme, ThemeError, css_override, load_theme


def test_builtins_and_default():
    assert load_theme(None).name == "bokken"
    assert load_theme("plain").brand_label == "Run report"


def test_custom_theme_file(tmp_path):
    f = tmp_path / "acme.json"
    f.write_text(json.dumps({"brand": "#0f766e", "brand_label": "Acme", "footer": "Acme runs."}))
    theme = load_theme(str(f))
    assert theme.brand == "#0f766e" and theme.brand_label == "Acme"
    assert "--accent:#0f766e" in css_override(theme)


def test_bad_theme_refuses(tmp_path):
    with pytest.raises(ThemeError, match="not a builtin"):
        load_theme("no-such-theme")
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"brand": "teal"}))
    with pytest.raises(ThemeError, match="hex"):
        load_theme(str(f))


def test_malformed_theme_file_refuses_as_theme_error(tmp_path):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not json")
    with pytest.raises(ThemeError, match="not valid JSON"):
        load_theme(str(malformed))
    listy = tmp_path / "listy.json"
    listy.write_text(json.dumps(["#0f766e"]))
    with pytest.raises(ThemeError, match="JSON object"):
        load_theme(str(listy))


def test_theme_reaches_both_surfaces(tmp_path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from bokken.demo import run_demo
    from bokken.report.generate import generate_report

    result = run_demo("themed")
    theme_file = tmp_path / "acme.json"
    theme_file.write_text(
        json.dumps({"brand": "#0f766e", "brand_dark": "#0b5a53", "brand_label": "Acme"})
    )
    _pptx, html = generate_report(result["session_dir"], theme_spec=str(theme_file))
    page = html.read_text()
    assert "--accent:#0f766e" in page and "Acme</b> · run report" in page
    assert Theme(name="x").brand not in page.split("</style>")[0].split(":root{--accent:")[-1][:8]

    # A malformed theme file refuses cleanly on export instead of stack-tracing.
    from typer.testing import CliRunner

    from bokken.cli.app import app

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not json")
    refused = CliRunner().invoke(app, ["export", "themed", "--theme", str(malformed)])
    assert refused.exit_code == 2
    assert "not valid JSON" in refused.stderr
