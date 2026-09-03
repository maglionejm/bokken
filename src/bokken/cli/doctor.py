"""One-screen environment diagnosis: every row is a fact plus the fix command.

Offline by default; `--network` adds provider reachability probes. Never
prints secrets - only presence.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from bokken.journal.workspace import workspace_root


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _extra(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _chromium_hint() -> bool:
    cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    linux = Path.home() / ".cache" / "ms-playwright"
    for root in (cache, linux):
        if root.exists() and any(p.name.startswith("chromium") for p in root.iterdir()):
            return True
    return False


def _reachable(host: str) -> bool:
    import socket

    try:
        socket.create_connection((host, 443), timeout=4).close()
        return True
    except OSError:
        return False


def run_checks(*, network: bool = False) -> list[Check]:
    import bokken

    checks: list[Check] = [Check("bokken", True, f"v{bokken.__version__}")]

    root = workspace_root()
    writable = os.access(root.parent if not root.exists() else root, os.W_OK)
    checks.append(
        Check(
            "workspace",
            writable,
            f"{root} ({'exists' if root.exists() else 'will be created'})",
            "" if writable else "set BOKKEN_HOME to a writable directory",
        )
    )

    for key, why in (
        ("ANTHROPIC_API_KEY", "default provider"),
        ("OPENAI_API_KEY", "openai provider"),
    ):
        present = bool(os.environ.get(key))
        checks.append(
            Check(
                key,
                present,
                "present" if present else f"not set ({why})",
                "" if present else f"export {key}=... (or run `bokken demo` - it needs no key)",
            )
        )

    ui = _extra("playwright")
    checks.append(
        Check(
            "[ui] extra",
            ui,
            "playwright installed" if ui else "not installed (walkthrough + feature tests skip)",
            "" if ui else "uv sync --extra ui  # or: pip install 'bokken[ui]'",
        )
    )
    if ui:
        chromium = _chromium_hint() or shutil.which("chromium") is not None
        checks.append(
            Check(
                "chromium",
                chromium,
                "browser cached" if chromium else "no browser found",
                "" if chromium else "uvx playwright install chromium",
            )
        )

    interview = _extra("twilio")
    checks.append(
        Check(
            "[interview] extra",
            interview,
            "twilio installed" if interview else "not installed (terminal channel still works)",
            "" if interview else "pip install 'bokken[interview]'",
        )
    )
    if interview:
        creds = all(
            os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM")
        )
        checks.append(
            Check(
                "twilio credentials",
                creds,
                "present" if creds else "TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM not all set",
                "" if creds else "export the three TWILIO_* variables (env only, never journaled)",
            )
        )

    checks.append(
        Check(
            "[openai] extra",
            _extra("openai"),
            "installed" if _extra("openai") else "not installed",
            "" if _extra("openai") else "pip install 'bokken[openai]'",
        )
    )

    roots = os.environ.get("BOKKEN_INPUT_ROOTS")
    checks.append(
        Check(
            "input roots (MCP)",
            True,
            roots or "default (workspace + server cwd)",
        )
    )

    if network:
        for host, label in (("api.anthropic.com", "anthropic"), ("api.openai.com", "openai")):
            up = _reachable(host)
            checks.append(
                Check(
                    f"{label} reachability",
                    up,
                    "reachable" if up else f"cannot reach {host}:443",
                    "" if up else "check proxy/firewall; corporate TLS interception breaks SDKs",
                )
            )
    return checks
