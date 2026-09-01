"""Insights library: learnings compound across runs instead of evaporating.

One JSONL record per finalized session under BOKKEN_HOME. New runs against
the same product seed their research with what earlier runs already
supported, contradicted, or found broken - with session provenance on every
line, so borrowed learnings are never laundered into fresh evidence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from bokken.journal import replay
from bokken.journal.store import read_events
from bokken.journal.workspace import workspace_root

LIBRARY_FILENAME = "library.jsonl"


def _library_path() -> Path:
    return workspace_root() / LIBRARY_FILENAME


def _product_key(brief: dict) -> str:
    inputs = brief.get("inputs") or {}
    return str(inputs.get("repo") or brief.get("problem_space", ""))[:200]


def append_learnings(session_dir: Path) -> dict | None:
    """Summarize a finalized session into the library; returns the record."""
    events = list(read_events(session_dir))
    state = replay(events)
    if state.stage != "complete":
        return None
    verdict = next(
        (
            d.resolution
            for d in state.decisions.values()
            if d.question == "kill, iterate, or proceed"
        ),
        None,
    )
    ui_findings = [
        e.payload["content"][:220]
        for e in events
        if e.type == "evidence.captured"
        and e.payload.get("source") == "ui_feature_test"
        and "broken" in e.payload.get("content", "")
    ]
    opportunities = [i.statement[:220] for i in state.insights.values() if i.kind == "opportunity"]
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "session": state.name,
        "product": _product_key(state.brief),
        "verdict": verdict,
        "assumptions": [
            {"statement": a.statement[:220], "score": a.score or "untested"}
            for a in state.assumptions.values()
        ],
        "opportunities": opportunities[:8],
        "ui_broken": ui_findings[:6],
    }
    path = _library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = {(r["session"], r["product"]) for r in read_learnings()}
    if (record["session"], record["product"]) in seen:
        return None  # finalization is idempotent; so is the library
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_learnings(product: str | None = None) -> list[dict]:
    path = _library_path()
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if product:
        records = [r for r in records if r["product"] == product]
    return records


def prior_learnings_text(brief: dict, *, exclude_session: str = "") -> str:
    """Prompt-ready digest of what earlier runs on this product established."""
    records = [r for r in read_learnings(_product_key(brief)) if r["session"] != exclude_session]
    if not records:
        return "(no prior runs on this product)"
    lines: list[str] = []
    for r in records[-4:]:
        lines.append(f"Run '{r['session']}' ended {r['verdict'] or 'incomplete'}:")
        for a in r["assumptions"]:
            if a["score"] in ("supported", "contradicted"):
                lines.append(f"  - [{a['score']}] {a['statement']}")
        for finding in r["ui_broken"][:2]:
            lines.append(f"  - [ui broken] {finding}")
    return "\n".join(lines) or "(prior runs recorded no scored learnings)"
