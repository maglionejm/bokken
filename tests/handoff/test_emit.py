"""Handoff adapters: executable renderings over the canonical package (issue #48)."""

from __future__ import annotations

import pytest

from bokken.demo import run_demo
from bokken.handoff.emit import EmitError, emit_adapters


@pytest.fixture(scope="module")
def finalized(tmp_path_factory):
    home = tmp_path_factory.mktemp("emit-home")
    mp = pytest.MonkeyPatch()
    mp.setenv("BOKKEN_HOME", str(home))
    mp.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        yield run_demo("emittable")
    finally:
        mp.undo()


def test_claude_code_adapter_is_executable_prose(finalized):
    written = emit_adapters(finalized["session_dir"], ["claude-code"])
    paths = {p.name for p in written}
    assert paths == {"HANDOFF.md", "build-mvp.md"}
    handoff_md = next(p for p in written if p.name == "HANDOFF.md").read_text()
    assert "How to execute" in handoff_md
    assert "dossier/dossier.json" in handoff_md and "journal.jsonl" in handoff_md
    assert "openspec validate --strict" in handoff_md
    assert "## Task plan" in handoff_md
    command = next(p for p in written if p.name == "build-mvp.md")
    assert ".claude/commands" in str(command)


def test_all_targets_emit_and_unknown_refuses(finalized):
    written = emit_adapters(finalized["session_dir"], ["cursor", "codex"])
    names = {str(p).split("adapters/")[1] for p in written}
    assert "cursor/.cursor/rules/bokken-handoff.mdc" in names
    assert "codex/AGENTS.md" in names
    with pytest.raises(EmitError, match="unknown emit target"):
        emit_adapters(finalized["session_dir"], ["copilot"])


def test_emit_without_package_refuses(tmp_path):
    with pytest.raises(EmitError, match="bokken handoff"):
        emit_adapters(tmp_path, ["claude-code"])
