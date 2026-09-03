"""Report themes: brand the deliverables without touching their truthfulness.

A theme changes chrome (colors, footer attribution, brand label) - never
content. v1 themes the HTML fully and the deck's footer; the deck palette
and a locale switch land with the page decomposition.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class ThemeError(ValueError):
    pass


@dataclass(frozen=True)
class Theme:
    name: str
    brand: str = "#c73e3a"  # --accent
    brand_dark: str = "#8a2b28"  # --accent-dark
    brand_label: str = "Bokken"
    footer: str = "Generated from the append-only Journal.<br>No manual edits."


BUILTIN: dict[str, Theme] = {
    "bokken": Theme(name="bokken"),
    "plain": Theme(
        name="plain",
        brand="#31435f",
        brand_dark="#1f2c40",
        brand_label="Run report",
        footer="Generated from an append-only run ledger.<br>No manual edits.",
    ),
}


def load_theme(spec: str | None) -> Theme:
    """`spec` is a builtin name, a JSON file path, or None (-> bokken)."""
    if not spec:
        return BUILTIN["bokken"]
    if spec in BUILTIN:
        return BUILTIN[spec]
    path = Path(spec)
    if not path.exists():
        raise ThemeError(f"unknown theme {spec!r}: not a builtin {sorted(BUILTIN)} nor a file")
    data = json.loads(path.read_text(encoding="utf-8"))
    theme = Theme(
        name=data.get("name", path.stem),
        brand=data.get("brand", BUILTIN["bokken"].brand),
        brand_dark=data.get("brand_dark", data.get("brand", BUILTIN["bokken"].brand_dark)),
        brand_label=data.get("brand_label", "Bokken"),
        footer=data.get("footer", BUILTIN["bokken"].footer),
    )
    for value in (theme.brand, theme.brand_dark):
        if not _HEX.match(value):
            raise ThemeError(f"theme colors must be #rrggbb hex, got {value!r}")
    return theme


def css_override(theme: Theme) -> str:
    return f":root{{--accent:{theme.brand};--accent-dark:{theme.brand_dark}}}"
