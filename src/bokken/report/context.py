"""ReportContext: everything the renderers need, derived once, no model calls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bokken.dossier.model import ArtifactNode, DossierModel

# Bookkeeping artifacts (rosters, exports) are never shown as prototype output.
EXCLUDED_ARTIFACT_KINDS = {
    "panel_manifest",
    "dossier_markdown",
    "dossier_json",
    "handoff_spec",
    "handoff_package",
    "report_deck",
    "report_page",
}

# List prices per million tokens (input, output); estimates only, labeled as such.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
DEFAULT_PRICE = (5.0, 25.0)


@dataclass(frozen=True)
class ModelUsageLine:
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class SpecEntry:
    capability: str
    sentence: str
    path: str


@dataclass(frozen=True)
class ReportContext:
    model: DossierModel
    usage: list[ModelUsageLine]
    total_cost_usd: float
    spec_entries: list[SpecEntry]
    handoff_refusal: str | None
    synthetic_evidence: int
    register_counts: dict[str, int]  # supported / contradicted / untested
    loopbacks: list[str]
    prototype_artifacts: list[ArtifactNode]
    dossier_paths: list[str] = field(default_factory=list)

    @property
    def headline(self) -> str:
        """A title-sized line: the problem space's first sentence, capped for display."""
        space = str(self.model.brief.get("problem_space", "") or self.model.name)
        line = first_sentence(space)
        return line if len(line) <= 140 else line[:137].rstrip() + "..."


def split_losers(options: list[str]) -> list[tuple[str, str]]:
    """Decision options encode losers inline as '<statement> [lost: <why>]'."""
    losers = []
    for option in options:
        if " [lost: " in option:
            statement, _, why = option.partition(" [lost: ")
            losers.append((statement, why.rstrip("]")))
    return losers


_FIRST_SENTENCE = re.compile(r"(.+?[.!?])(\s|$)")


def first_sentence(text: str) -> str:
    flat = " ".join(text.split())
    match = _FIRST_SENTENCE.match(flat)
    return match.group(1) if match else flat


def _purpose_sentence(spec_file: Path) -> str:
    lines = spec_file.read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    in_purpose = False
    for line in lines:
        if line.startswith("## "):
            if in_purpose:
                break
            in_purpose = line.strip().lower() == "## purpose"
            continue
        if in_purpose and line.strip():
            body.append(line.strip())
    return first_sentence(" ".join(body)) if body else "(purpose not stated)"


def _spec_entries(session_dir: Path) -> list[SpecEntry]:
    entries: list[SpecEntry] = []
    for spec_file in sorted((session_dir / "handoff").glob("openspec/changes/*/specs/*/spec.md")):
        entries.append(
            SpecEntry(
                capability=spec_file.parent.name,
                sentence=_purpose_sentence(spec_file),
                path=str(spec_file.relative_to(session_dir)),
            )
        )
    return entries


def _handoff_refusal(model: DossierModel) -> str | None:
    if model.recommendation and model.recommendation.resolution == "kill":
        return "the test recommendation is 'kill': a killed concept has no build handoff"
    return None


def build_context(session_dir: Path, model: DossierModel) -> ReportContext:
    per_model: dict[str, dict[str, int]] = {}
    for trace in model.model_traces:
        bucket = per_model.setdefault(trace.model, {"calls": 0, "in": 0, "out": 0})
        bucket["calls"] += 1
        bucket["in"] += trace.usage.get("input_tokens", 0)
        bucket["out"] += trace.usage.get("output_tokens", 0)
    usage = []
    for name in sorted(per_model):
        b = per_model[name]
        p_in, p_out = PRICE_PER_MTOK.get(name, DEFAULT_PRICE)
        usage.append(
            ModelUsageLine(
                model=name,
                calls=b["calls"],
                input_tokens=b["in"],
                output_tokens=b["out"],
                cost_usd=b["in"] / 1e6 * p_in + b["out"] / 1e6 * p_out,
            )
        )

    spec_entries = _spec_entries(session_dir)
    register_counts = {"supported": 0, "contradicted": 0, "untested": 0}
    for a in model.assumptions.values():
        register_counts[a.score or "untested"] += 1

    dossier_paths = [
        p for p in ("dossier/dossier.md", "dossier/dossier.json") if (session_dir / p).exists()
    ]
    return ReportContext(
        model=model,
        usage=usage,
        total_cost_usd=sum(u.cost_usd for u in usage),
        spec_entries=spec_entries,
        handoff_refusal=None if spec_entries else _handoff_refusal(model),
        synthetic_evidence=sum(1 for e in model.evidence.values() if e.synthetic),
        register_counts=register_counts,
        loopbacks=[
            f"{t.from_stage} -> {t.to_stage}: {t.condition}"
            for t in model.transitions
            if t.loopback
        ],
        prototype_artifacts=[a for a in model.artifacts if a.kind not in EXCLUDED_ARTIFACT_KINDS],
        dossier_paths=dossier_paths,
    )
