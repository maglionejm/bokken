"""Build dist/bokken-<version>.mcpb: the manifest template with the released
version injected, zipped in the MCP Bundle layout (manifest.json at the root).

The bundle wraps `uvx bokken==<version> serve`, so the server users run is
always the published package - the bundle carries configuration, not code.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import bokken

ROOT = Path(__file__).parent.parent


def main() -> None:
    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))
    manifest["version"] = bokken.__version__
    manifest["server"]["mcp_config"]["args"] = [f"bokken=={bokken.__version__}", "serve"]
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"bokken-{bokken.__version__}.mcpb"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
