"""Run finalization: after a run completes, produce the Dossier, the handoff, the report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bokken.handoff.generate import (
    HandoffFormatError,
    HandoffGenerationError,
    HandoffRefusedError,
    generate_handoff,
    handoff_exists,
)
from bokken.journal import read_events, replay
from bokken.stages.base import RouterFactory


@dataclass(frozen=True)
class FinalizeResult:
    dossier_generated: bool = False
    handoff_generated: bool = False
    handoff_skipped: str | None = None
    report_generated: bool = False
    report_theme_fallback: str | None = None

    def summary(self) -> str:
        parts = []
        if self.dossier_generated:
            parts.append("dossier generated")
        if self.handoff_generated:
            parts.append("handoff specs generated")
        if self.handoff_skipped:
            parts.append(f"handoff skipped: {self.handoff_skipped}")
        if self.report_generated:
            note = "report exported (pptx + html)"
            if self.report_theme_fallback:
                note += (
                    " with the default theme; the journaled theme was unusable "
                    f"({self.report_theme_fallback})"
                )
            parts.append(note)
        return "; ".join(parts) or "already finalized"


def _dossier_exists(session_dir: Path) -> bool:
    return any(
        e.type == "artifact.generated" and e.payload.get("kind") == "dossier_markdown"
        for e in read_events(session_dir)
    )


def finalize_session(session_dir: Path, router_factory: RouterFactory) -> FinalizeResult:
    """Idempotent: generates only what does not exist yet. Dossier, then handoff, then report."""
    state = replay(read_events(session_dir))
    if state.stage != "complete":
        return FinalizeResult(handoff_skipped="session is not complete")

    dossier_generated = False
    if not _dossier_exists(session_dir):
        from bokken.dossier import generate

        generate(session_dir)
        dossier_generated = True

    handoff_generated = False
    handoff_skipped: str | None = None
    if not handoff_exists(session_dir):
        try:
            generate_handoff(session_dir, router_factory)
            handoff_generated = True
        except HandoffRefusedError as refusal:
            handoff_skipped = str(refusal)
        except (HandoffGenerationError, HandoffFormatError) as error:
            # generation/format failure must not block the dossier/report
            # pipeline; `bokken handoff <name>` retries it on demand
            handoff_skipped = f"generation failed (retry with `bokken handoff`): {error}"

    report_generated = False
    report_theme_fallback: str | None = None
    from bokken.report.generate import generate_report, report_exists
    from bokken.report.theme import ThemeError

    if not report_exists(session_dir):
        try:
            generate_report(session_dir)
        except ThemeError as error:
            # A broken journaled theme must not kill finalization: the report
            # is the deliverable, the chrome is not. Regenerate with the
            # default theme and say so in the summary.
            generate_report(session_dir, theme_spec="bokken")
            report_theme_fallback = str(error)
        report_generated = True

    from bokken.library import append_learnings

    append_learnings(session_dir)

    return FinalizeResult(
        dossier_generated=dossier_generated,
        handoff_generated=handoff_generated,
        handoff_skipped=handoff_skipped,
        report_generated=report_generated,
        report_theme_fallback=report_theme_fallback,
    )
