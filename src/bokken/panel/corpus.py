"""Evidence corpus: typed, content-addressed sources with line-addressable spans.

Source kinds: ``code`` (an app repository the agents explore), ``metrics``
(business/performance data), ``discussion`` (interviews, meeting notes, needs
statements), and ``document`` (other textual material).

Ingestion is deliberately narrow: only allowlisted suffixes are read (for
explicitly named files as well as for directory walks), every file is capped,
and each ingested set has a total budget so one directory cannot balloon the
corpus. Paths supplied by an untrusted caller (the MCP surface) are additionally
confined to an authorized root; whatever is refused or skipped is reported, never
dropped in silence.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from bokken.journal.schema import short_id
from bokken.journal.workspace import workspace_root

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
FILE_SIZE_CAP = 200_000  # bytes per ingested file
CORPUS_SIZE_CAP = 4_000_000  # bytes per ingested set (text inputs, repo walk)

# Root confinement for client-supplied input paths (see ``input_roots``).
INPUT_ROOTS_ENV = "BOKKEN_INPUT_ROOTS"


class InputPathRefused(ValueError):
    """A caller-supplied input path escapes the authorized input root."""


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
    source_id = short_id(f"{name}\n{content}")
    return Source(source_id=source_id, name=name, kind=kind, lines=tuple(content.splitlines()))


def input_roots(base: Path | None = None) -> tuple[Path, ...]:
    """The roots a caller-supplied input path may resolve inside.

    Default: the workspace root (``BOKKEN_HOME``, else ``./.bokken``) and the
    working directory the process was started in — where sessions already live.
    An operator who genuinely wants a wider reach says so explicitly with
    ``BOKKEN_INPUT_ROOTS`` (``os.pathsep``-separated), which replaces the
    default entirely.
    """
    override = os.environ.get(INPUT_ROOTS_ENV)
    if override:
        roots = [Path(part).resolve() for part in override.split(os.pathsep) if part.strip()]
        if roots:
            return tuple(dict.fromkeys(roots))
    candidates = [workspace_root(base).resolve(), (base or Path.cwd()).resolve()]
    return tuple(dict.fromkeys(candidates))


def _within(path: Path, roots: Sequence[Path]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def confine_path(raw: str, roots: Sequence[Path]) -> Path:
    """Resolve one caller-supplied path inside ``roots`` or refuse it.

    Traversal (``../``), symlinks pointing out, and absolute paths outside the
    roots are all refused — the resolved real path must lie inside a root.
    """
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = roots[0] / candidate
    resolved = candidate.resolve()
    listed = ", ".join(str(root) for root in roots)
    if not _within(resolved, roots):
        raise InputPathRefused(
            f"input path {raw!r} resolves to {resolved} which is outside the authorized "
            f"input root(s) [{listed}]; move the input inside, or widen "
            f"{INPUT_ROOTS_ENV} deliberately"
        )
    if not resolved.exists():
        raise InputPathRefused(f"input path {raw!r} does not exist under [{listed}]")
    return resolved


def confine_inputs(inputs: dict, roots: Sequence[Path]) -> dict:
    """Rewrite a brief's ``inputs`` block to resolved paths inside ``roots``.

    Refusal is loud and up front: an escaping path, a missing path, or a named
    file outside the text allowlist aborts session creation instead of being
    discovered halfway through a run.
    """
    confined = dict(inputs)
    for key in ("metrics", "discussions", "documents"):
        declared = inputs.get(key) or []
        resolved = [confine_path(raw, roots) for raw in declared]
        for path in resolved:
            if path.is_file() and path.suffix.lower() not in TEXT_SUFFIXES:
                allowed = " ".join(sorted(TEXT_SUFFIXES))
                raise InputPathRefused(
                    f"input file {str(path)!r} is not in the text allowlist ({allowed}); "
                    "declare a supported text file or a directory of them"
                )
        confined[key] = [str(path) for path in resolved]
    if inputs.get("repo"):
        confined["repo"] = str(confine_path(inputs["repo"], roots))
    return confined


@dataclass(frozen=True)
class SkippedInput:
    """A declared input that did not enter the corpus, and why."""

    path: str
    reason: str


def _as_roots(roots: Iterable[str | Path] | None) -> tuple[Path, ...] | None:
    if roots is None:
        return None
    resolved = tuple(Path(root).resolve() for root in roots)
    return resolved or None


def _expand(
    paths: list[Path],
    suffixes: set[str],
    *,
    roots: Sequence[Path] | None = None,
) -> tuple[list[Path], list[SkippedInput]]:
    """Resolve declared paths to readable files, reporting what was left out.

    The suffix allowlist applies to explicitly named files too, not only to
    directory walks; every file is size-capped and the set has a total budget.
    """
    files: list[Path] = []
    skipped: list[SkippedInput] = []
    remaining = CORPUS_SIZE_CAP
    capped = False

    def take(path: Path, *, declared: bool) -> None:
        nonlocal remaining, capped
        if roots is not None and not _within(path.resolve(), roots):
            skipped.append(SkippedInput(str(path), "outside the authorized input root"))
            return
        if path.suffix.lower() not in suffixes:
            if declared:
                allowed = " ".join(sorted(suffixes))
                skipped.append(
                    SkippedInput(str(path), f"suffix not in the text allowlist ({allowed})")
                )
            return
        size = path.stat().st_size
        if size > FILE_SIZE_CAP:
            skipped.append(
                SkippedInput(str(path), f"larger than the {FILE_SIZE_CAP}-byte file cap")
            )
            return
        if size > remaining:
            # One report per ingested set, not one per file left behind.
            if not capped:
                skipped.append(
                    SkippedInput(str(path), f"would exceed the {CORPUS_SIZE_CAP}-byte corpus cap")
                )
            capped = True
            return
        remaining -= size
        files.append(path)

    for path in paths:
        if roots is not None and not _within(path.resolve(), roots):
            skipped.append(SkippedInput(str(path), "outside the authorized input root"))
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if capped:
                    break
                if child.is_file():
                    take(child, declared=False)
        elif path.is_file():
            take(path, declared=True)
        else:
            skipped.append(SkippedInput(str(path), "not found on the server"))
    return files, skipped


class Corpus:
    def __init__(self, sources: list[Source], skipped: Iterable[SkippedInput] = ()) -> None:
        self._sources = {s.source_id: s for s in sources}
        self.skipped: tuple[SkippedInput, ...] = tuple(skipped)

    @classmethod
    def ingest(cls, paths: list[Path], kind: SourceKind = "document") -> Corpus:
        files, skipped = _expand(paths, TEXT_SUFFIXES)
        return cls([_read_source(f, f.name, kind) for f in files], skipped)

    @classmethod
    def ingest_inputs(
        cls,
        inputs: dict,
        base: Path | None = None,
        roots: Iterable[str | Path] | None = None,
    ) -> Corpus:
        """Build the corpus from a brief's typed ``inputs`` block.

        ``roots``, when given (sessions created over MCP journal theirs in the
        config snapshot), confines every input path: anything resolving outside
        is skipped and reported rather than read.
        """
        base_dir = base or Path.cwd()
        confinement = _as_roots(roots)

        def resolve(raw: str) -> Path:
            path = Path(raw)
            return path if path.is_absolute() else base_dir / path

        sources: list[Source] = []
        skipped: list[SkippedInput] = []
        for kind, key in (
            ("metrics", "metrics"),
            ("discussion", "discussions"),
            ("document", "documents"),
        ):
            paths = [resolve(p) for p in inputs.get(key, [])]
            files, left_out = _expand(paths, TEXT_SUFFIXES, roots=confinement)
            sources.extend(
                _read_source(f, f.name, kind)  # type: ignore[arg-type]
                for f in files
            )
            skipped.extend(left_out)
        repo = inputs.get("repo")
        if repo:
            repo_sources, repo_skipped = ingest_repo(resolve(repo), roots=confinement)
            sources.extend(repo_sources)
            skipped.extend(repo_skipped)
        return cls(sources, skipped)

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


def ingest_repo(
    repo_root: Path, *, roots: Sequence[Path] | None = None
) -> tuple[list[Source], list[SkippedInput]]:
    """Ingest an app repository as citable ``code`` sources, named by relative path.

    Returns the sources plus whatever was refused at the declared-input level
    (a repo outside the authorized roots, a missing directory, or a walk that
    hit the corpus cap); per-file allowlist and size filtering stays quiet by
    design, it is the documented shape of a repo walk.
    """
    sources: list[Source] = []
    if roots is not None and not _within(repo_root.resolve(), roots):
        return sources, [SkippedInput(str(repo_root), "outside the authorized input root")]
    if not repo_root.is_dir():
        return sources, [SkippedInput(str(repo_root), "not a directory on the server")]
    remaining = CORPUS_SIZE_CAP
    for file in sorted(repo_root.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(repo_root)
        if any(part in REPO_EXCLUDED_DIRS for part in relative.parts):
            continue
        if file.suffix.lower() not in CODE_SUFFIXES:
            continue
        if roots is not None and not _within(file.resolve(), roots):
            continue
        size = file.stat().st_size
        if size > FILE_SIZE_CAP:
            continue
        if size > remaining:
            return sources, [
                SkippedInput(
                    str(repo_root),
                    f"repo walk truncated at the {CORPUS_SIZE_CAP}-byte corpus cap",
                )
            ]
        remaining -= size
        sources.append(_read_source(file, str(relative), "code"))
    return sources, []
