"""Generate the report exports: report/report.pptx and report/report.html."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bokken.dossier.model import build_model
from bokken.journal import Actor, read_events
from bokken.journal.store import JournalStore
from bokken.report.context import build_context

REPORT_ACTOR = Actor(kind="system", name="report")
REPORT_KINDS = ("report_deck", "report_page")


class ReportError(RuntimeError):
    """The session cannot be reported (unknown or empty)."""


def report_exists(session_dir: Path) -> bool:
    kinds = {
        e.payload.get("kind") for e in read_events(session_dir) if e.type == "artifact.generated"
    }
    return all(kind in kinds for kind in REPORT_KINDS)


def generate_report(session_dir: Path) -> tuple[Path, Path]:
    """Deterministic, journal-only. Writes both files and journals them as artifacts."""
    from bokken.report.deck import render_deck
    from bokken.report.page import render_page

    model = build_model(session_dir)
    if not model.transitions and not model.evidence:
        raise ReportError("nothing to report: the session has no substantive events yet")
    ctx = build_context(session_dir, model)

    report_dir = session_dir / "report"
    pptx_path = report_dir / "report.pptx"
    html_path = report_dir / "report.html"
    render_deck(ctx, pptx_path)
    report_dir.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_page(ctx), encoding="utf-8")

    with JournalStore.open(session_dir) as store:
        for path, kind in ((pptx_path, "report_deck"), (html_path, "report_page")):
            store.append(
                type="artifact.generated",
                stage=None,
                actor=REPORT_ACTOR,
                payload={
                    "path": str(path.relative_to(session_dir)),
                    "kind": kind,
                    "content_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                },
            )
    return pptx_path, html_path
