"""Evidence corpus: typed, content-addressed sources with line-addressable spans.

Source kinds: ``code`` (an app repository the agents explore), ``metrics``
(business/performance data), ``discussion`` (interviews, meeting notes, needs
statements), and ``document`` (other textual material).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

SourceKind = Literal["document", "discussion", "metrics", "code"]

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json"}

# Repo ingestion allowlist: source and configuration files agents can usefully read.
CODE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".swift",
    ".c",
    ".h",
    ".cpp",
    ".cs",
    ".sql",
    ".sh",
    ".html",
    ".css",
    ".vue",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".cfg",
    ".ini",
    ".txt",
}
REPO_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "target",
    "vendor",
    ".bokken",
}
REPO_FILE_SIZE_CAP = 200_000  # bytes per file


class Citation(BaseModel):
    source_id: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Source:
    source_id: str
    name: str
    kind: SourceKind
    lines: tuple[str, ...]


def _read_source(file: Path, name: str, kind: SourceKind) -> Source:
    content = file.read_text(encoding="utf-8", errors="replace")
    source_id = hashlib.sha256(f"{name}\n{content}".encode()).hexdigest()[:12]
    return Source(source_id=source_id, name=name, kind=kind, lines=tuple(content.splitlines()))


def _expand(paths: list[Path], suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                p for p in sorted(path.rglob("*")) if p.is_file() and p.suffix.lower() in suffixes
            )
        elif path.is_file():
            files.append(path)
    return files


class Corpus:
    def __init__(self, sources: list[Source]) -> None:
        self._sources = {s.source_id: s for s in sources}

    @classmethod
    def ingest(cls, paths: list[Path], kind: SourceKind = "document") -> Corpus:
        return cls([_read_source(f, f.name, kind) for f in _expand(paths, TEXT_SUFFIXES)])

    @classmethod
    def ingest_inputs(cls, inputs: dict, base: Path | None = None) -> Corpus:
        """Build the corpus from a brief's typed ``inputs`` block."""
        root = base or Path.cwd()

        def resolve(raw: str) -> Path:
            path = Path(raw)
            return path if path.is_absolute() else root / path

        sources: list[Source] = []
        for kind, key in (
            ("metrics", "metrics"),
            ("discussion", "discussions"),
            ("document", "documents"),
        ):
            paths = [resolve(p) for p in inputs.get(key, [])]
            sources.extend(
                _read_source(f, f.name, kind)  # type: ignore[arg-type]
                for f in _expand(paths, TEXT_SUFFIXES)
            )
        repo = inputs.get("repo")
        if repo:
            sources.extend(ingest_repo(resolve(repo)))
        return cls(sources)

    @property
    def source_ids(self) -> list[str]:
        return list(self._sources)

    def ids_of_kind(self, *kinds: SourceKind) -> list[str]:
        return [s.source_id for s in self._sources.values() if s.kind in kinds]

    def kind_of(self, source_id: str) -> SourceKind | None:
        source = self._sources.get(source_id)
        return source.kind if source else None

    def span(self, citation: Citation) -> str | None:
        source = self._sources.get(citation.source_id)
        if source is None:
            return None
        if citation.start_line < 1 or citation.end_line > len(source.lines):
            return None
        if citation.start_line > citation.end_line:
            return None
        text = "\n".join(source.lines[citation.start_line - 1 : citation.end_line])
        return text if text.strip() else None

    def validate_citation(self, citation: Citation) -> bool:
        return self.span(citation) is not None

    def context_for(self, scope: list[str] | None = None) -> str:
        """Render the (scoped) corpus as question context for persona turns."""
        ids = scope or self.source_ids
        blocks = []
        for source_id in ids:
            source = self._sources.get(source_id)
            if source:
                numbered = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(source.lines))
                blocks.append(f"[source {source_id} ({source.kind}) - {source.name}]\n{numbered}")
        return "\n\n".join(blocks)


def ingest_repo(repo_root: Path) -> list[Source]:
    """Ingest an app repository as citable ``code`` sources, named by relative path."""
    sources: list[Source] = []
    if not repo_root.is_dir():
        return sources
    for file in sorted(repo_root.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(repo_root)
        if any(part in REPO_EXCLUDED_DIRS for part in relative.parts):
            continue
        if file.suffix.lower() not in CODE_SUFFIXES:
            continue
        if file.stat().st_size > REPO_FILE_SIZE_CAP:
            continue
        sources.append(_read_source(file, str(relative), "code"))
    return sources
