"""Session Dossier generation: Parts A/B/C from the Journal alone."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from bokken.dossier.model import DOSSIER_SCHEMA_VERSION, DossierModel, build_model
from bokken.dossier.render import DOJO_BANNER, render_json, render_markdown
from bokken.journal import Actor, JournalStore

GENERATOR_ACTOR = Actor(kind="system", name="dossier")


def generate(session_dir: Path) -> tuple[Path, Path, str]:
    """Generate dossier.md and dossier.json from the journal. No model calls.

    Returns (markdown_path, json_path, status).
    """
    model = build_model(session_dir)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    markdown = render_markdown(model, generated_at)
    document = render_json(model, generated_at)

    out_dir = session_dir / "dossier"
    out_dir.mkdir(exist_ok=True)
    md_path = out_dir / "dossier.md"
    json_path = out_dir / "dossier.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(document, encoding="utf-8")

    with JournalStore.open(session_dir) as store:
        for path, kind, content in (
            (md_path, "dossier_markdown", markdown),
            (json_path, "dossier_json", document),
        ):
            store.append(
                type="artifact.generated",
                stage=None,
                actor=GENERATOR_ACTOR,
                payload={
                    "path": str(path.relative_to(session_dir)),
                    "kind": kind,
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                },
            )
    return md_path, json_path, model.status


__all__ = [
    "DOJO_BANNER",
    "DOSSIER_SCHEMA_VERSION",
    "DossierModel",
    "build_model",
    "generate",
    "render_json",
    "render_markdown",
]
