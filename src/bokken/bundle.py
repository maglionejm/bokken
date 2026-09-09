"""Pack a finalized session into one portable, self-describing archive.

The bundle is the run as an object: manifest + deliverables (+ the journal
and artifacts unless the caller asks for deliverables only). Nothing in it
is regenerated here - packing never mutates the session.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import bokken
from bokken.journal.store import read_events


class PackError(RuntimeError):
    pass


def _session_facts(session_dir: Path) -> dict:
    name = session_dir.name
    mode = stage = verdict = None
    first_ts = last_ts = None
    demo = False
    for event in read_events(session_dir):
        last_ts = event.ts.isoformat()
        if first_ts is None:
            first_ts = last_ts
        if event.type == "session.created":
            name = event.payload.get("name", name)
            mode = event.payload.get("mode")
            demo = bool(event.payload.get("config", {}).get("demo"))
        elif event.type == "transition.fired":
            stage = event.payload.get("to_stage")
        elif (
            event.type == "decision.recorded"
            and event.payload.get("question") == "kill, iterate, or proceed"
        ):
            verdict = event.payload.get("resolution")
    return {
        "session": name,
        "mode": mode,
        "stage": stage,
        "verdict": verdict,
        "demo": demo,
        "created_at": first_ts,
        "last_event_at": last_ts,
    }


def _cost(session_dir: Path) -> float:
    from bokken.dossier.model import build_model
    from bokken.report.context import cost_rows

    return round(sum(r["cost_usd"] for r in cost_rows(build_model(session_dir))), 2)


def _files_to_pack(session_dir: Path, deliverables_only: bool) -> list[Path]:
    wanted = [
        session_dir / "report" / "report.html",
        session_dir / "report" / "report.pptx",
        session_dir / "dossier" / "dossier.md",
    ]
    if not deliverables_only:
        wanted.append(session_dir / "dossier" / "dossier.json")
        wanted.append(session_dir / "journal.jsonl")
        wanted += sorted(p for p in (session_dir / "artifacts").rglob("*") if p.is_file())
    handoff_files = sorted(p for p in (session_dir / "handoff").rglob("*") if p.is_file())
    if deliverables_only:
        # Adapters carry evidence pointers into the journal and dossier.json,
        # which this pack omits; shipping them would hand out dead references.
        adapters_dir = session_dir / "handoff" / "adapters"
        handoff_files = [p for p in handoff_files if not p.is_relative_to(adapters_dir)]
    wanted += handoff_files
    return [p for p in wanted if p.exists()]


def pack_session(
    session_dir: Path, *, deliverables_only: bool = False, out: Path | None = None
) -> Path:
    """Write `<name>.bokken.zip` and return its path."""
    report = session_dir / "report" / "report.html"
    if not report.exists():
        raise PackError(
            f"session '{session_dir.name}' has no report yet - run `bokken export "
            f"{session_dir.name}` first"
        )
    files = _files_to_pack(session_dir, deliverables_only)
    index = []
    for f in files:
        data = f.read_bytes()
        index.append(
            {
                "path": str(f.relative_to(session_dir)),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "bokken_version": bokken.__version__,
        **_session_facts(session_dir),
        "cost_usd_list_price": _cost(session_dir),
        "contents": "deliverables-only" if deliverables_only else "full",
        "packed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": index,
    }
    if deliverables_only:
        manifest["omitted"] = (
            "journal, evidence graph (dossier.json), raw artifacts, and handoff "
            "adapters (their evidence pointers reference the omitted files) are "
            "omitted for external sharing; claims in the report remain "
            "journal-derived but are not independently verifiable from this "
            "bundle alone"
        )
    target = out or (session_dir.parent / f"{session_dir.name}.bokken.zip")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for f in files:
            zf.write(f, arcname=str(f.relative_to(session_dir)))
    return target
