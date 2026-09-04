"""The MCPB bundle must never drift from the server it wraps (issue #48 follow-up)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
MANIFEST = json.loads((ROOT / "mcpb" / "manifest.json").read_text())


async def test_manifest_tools_match_registered_tools():
    from bokken.mcp.server import mcp

    registered = {t.name for t in await mcp.list_tools()}
    declared = {t["name"] for t in MANIFEST["tools"]}
    assert declared == registered


def test_manifest_wraps_uvx_serve_and_never_hardcodes_secrets():
    cfg = MANIFEST["server"]["mcp_config"]
    assert cfg["command"] == "uvx"
    assert cfg["args"][-1] == "serve"
    assert MANIFEST["user_config"]["anthropic_api_key"]["sensitive"] is True
    raw = json.dumps(MANIFEST)
    assert "sk-" not in raw


def test_build_injects_release_version(tmp_path, monkeypatch):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_mcpb.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    bundle = Path(result.stdout.strip().splitlines()[-1])
    with zipfile.ZipFile(bundle) as zf:
        packed = json.loads(zf.read("manifest.json"))
    import bokken

    assert packed["version"] == bokken.__version__
    assert packed["server"]["mcp_config"]["args"][0] == f"bokken=={bokken.__version__}"
