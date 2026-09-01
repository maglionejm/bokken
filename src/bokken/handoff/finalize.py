"""Run finalization: after a run completes, produce the Dossier, the handoff, the report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bokken.handoff.generate import (
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

    def summary(self) -> str:
        parts = []
        if self.dossier_generated:
            parts.append("dossier generated")
        if self.handoff_generated:
            parts.append("handoff specs generated")
        if self.handoff_skipped:
            parts.append(f"handoff skipped: {self.handoff_skipped}")
        if self.report_generated:
            parts.append("report exported (pptx + html)")
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
        except HandoffGenerationError as error:
            # generation failure must not block the dossier/report pipeline;
            # `bokken handoff <name>` retries it on demand
            handoff_skipped = f"generation failed (retry with `bokken handoff`): {error}"

    report_generated = False
    from bokken.report.generate import generate_report, report_exists

    if not report_exists(session_dir):
        generate_report(session_dir)
        report_generated = True

    return FinalizeResult(
        dossier_generated=dossier_generated,
        handoff_generated=handoff_generated,
        handoff_skipped=handoff_skipped,
        report_generated=report_generated,
    )
