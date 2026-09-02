"""ReportContext: everything the renderers need, derived once, no model calls."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from bokken.dossier.model import ArtifactNode, DossierModel
from bokken.models.router import MODELS

# Bookkeeping artifacts (rosters, exports) are never shown as prototype output.
EXCLUDED_ARTIFACT_KINDS = {
    "panel_manifest",
    "opportunity_ranking",
    "ui_review",
    "ui_screenshot",
    "market_research",
    "ui_feature_tests",
    "dossier_markdown",
    "dossier_json",
    "handoff_spec",
    "handoff_package",
    "report_deck",
    "report_page",
}

# List prices per million tokens (input, output); estimates only, labeled as such.
# Derived from the model registry so every allowlisted model has a price.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {name: spec.price for name, spec in MODELS.items()}
MODEL_PROVIDER: dict[str, str] = {name: spec.provider for name, spec in MODELS.items()}
DEFAULT_PRICE = (5.0, 25.0)  # only for models journaled before joining the allowlist
DEFAULT_PROVIDER = "anthropic"  # ditto: price such a model on the house provider

# Cache multipliers on a model's input list price, per provider, because the two
# vendors bill the cached prefix differently: Anthropic charges a cache read at
# a tenth of input and a cache write at a premium over input, while OpenAI bills
# cached input at a reduced rate and never bills a separate cache write.
# Per-provider is the honest granularity available here: the registry carries
# one list price per model and no per-model cache price to read.
CACHE_MULTIPLIERS: dict[str, tuple[float, float]] = {  # (read, write)
    "anthropic": (0.1, 1.25),
    "openai": (0.1, 0.0),
}


def call_cost_usd(model: str, usage: Mapping[str, int]) -> float:
    """List-price estimate for one call's usage: the single pricing function.

    Every caller (the `costs` verb, the report appendix) prices through here, so
    one journaled trace can never be quoted at two different numbers. All four
    billed buckets count. Provider-side tool fees (a web search request charge,
    say) are not present in provider usage metadata at all, so they are absent
    from this estimate rather than guessed at."""
    p_in, p_out = PRICE_PER_MTOK.get(model, DEFAULT_PRICE)
    read_mult, write_mult = CACHE_MULTIPLIERS[MODEL_PROVIDER.get(model, DEFAULT_PROVIDER)]
    per_mtok = (
        int(usage.get("input_tokens", 0) or 0) * p_in
        + int(usage.get("output_tokens", 0) or 0) * p_out
        + int(usage.get("cache_read_tokens", 0) or 0) * p_in * read_mult
        + int(usage.get("cache_write_tokens", 0) or 0) * p_in * write_mult
    )
    return per_mtok / 1e6


@dataclass(frozen=True)
class ModelUsageLine:
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class SpecEntry:
    capability: str
    sentence: str
    path: str


@dataclass(frozen=True)
class ReportContext:
    session_dir: Path
    model: DossierModel
    usage: list[ModelUsageLine]
    total_cost_usd: float
    spec_entries: list[SpecEntry]
    handoff_refusal: str | None
    synthetic_evidence: int
    register_counts: dict[str, int]  # supported / contradicted / untested
    loopbacks: list[str]
    prototype_artifacts: list[ArtifactNode]
    opportunities: list[str] = field(default_factory=list)
    demo: bool = False  # demo sessions: usage is illustrative, $0.00 charged
    ui_review: str | None = None
    ui_screenshots: list[str] = field(default_factory=list)
    stage_digest: dict[str, dict] = field(default_factory=dict)
    market_research: dict | None = None
    ui_feature_results: list = field(default_factory=list)
    lens_votes: list[dict] = field(default_factory=list)
    skeptic_challenge: str | None = None
    kata_moves: list[dict] = field(default_factory=list)
    dissent: list[dict] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    hill: dict = field(default_factory=dict)  # who/what/wow/hypothesis from the one-pager
    dossier_paths: list[str] = field(default_factory=list)

    @property
    def headline(self) -> str:
        """A title-sized line: the problem space's first sentence, capped for display."""
        space = str(self.model.brief.get("problem_space", "") or self.model.name)
        line = first_sentence(space)
        return line if len(line) <= 140 else line[:137].rstrip() + "..."


def cost_rows(model: DossierModel) -> list[dict]:
    """One row per stage x prompt_id x class from journaled model calls."""
    rows: dict[tuple, dict] = {}
    for tr in model.model_traces:
        key = (tr.stage or "-", tr.prompt_id, tr.routing_class, tr.model)
        row = rows.setdefault(
            key,
            {
                "stage": key[0],
                "prompt_id": key[1],
                "class": key[2],
                "model": key[3],
                "calls": 0,
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
            },
        )
        row["calls"] += 1
        row["input"] += tr.usage.get("input_tokens", 0)
        row["output"] += tr.usage.get("output_tokens", 0)
        row["cache_read"] += tr.usage.get("cache_read_tokens", 0)
        row["cache_write"] += tr.usage.get("cache_write_tokens", 0)
    out = []
    for row in rows.values():
        row["cost_usd"] = round(call_cost_usd(row["model"], row_usage(row)), 4)
        out.append(row)
    return sorted(out, key=lambda r: -r["cost_usd"])


def row_usage(row: Mapping[str, int]) -> dict[str, int]:
    """A cost row's display keys read back as normalized usage buckets."""
    return {
        "input_tokens": row["input"],
        "output_tokens": row["output"],
        "cache_read_tokens": row["cache_read"],
        "cache_write_tokens": row["cache_write"],
    }


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


_OPP_SCORE = re.compile(r"opportunity (\d+(?:\.\d+)?)")


def _ranked_opportunities(model: DossierModel) -> list[str]:
    records = [i.statement for i in model.insights.values() if i.kind == "opportunity"]

    def score(statement: str) -> float:
        match = _OPP_SCORE.search(statement)
        return float(match.group(1)) if match else 0.0

    return sorted(records, key=score, reverse=True)


STAGE_PROCESS = {
    "empathize": "Corpus-calibrated interview program per segment; grounded persona "
    "interviews with citation-validated answers or honest abstention; functional UI "
    "walkthrough of the running app; JTBD desired-outcome derivation and per-persona "
    "Importance/Satisfaction scoring into a deterministic Ulwick opportunity ranking.",
    "define": "Evidence clustered into insights tied to underserved outcomes; "
    "point-of-view candidates drafted and reframed (HMW) when solution-shaped; winner "
    "selected on evidence + opportunity coverage with losers preserved.",
    "ideate": "Quota-driven work-alone divergence tied to outcome IDs with novelty "
    "monitoring; skeptic challenge on record; convergence through three firewalled "
    "lenses - adversarial feasibility vs the codebase (green/amber/red + first honest "
    "slice), independent RICE, outcome desirability.",
    "prototype": "Assumption register built and risk-classified (impact x uncertainty); "
    "cheapest artifact set chosen against the riskiest assumption; artifacts generated "
    "and hash-journaled with assumption linkage.",
    "test": "Fresh firewalled panel evaluates the prototype against every register "
    "entry; quantified kill/iterate/proceed recommendation with loop-back proposal on "
    "contradiction.",
}


def _stage_digest(model: DossierModel) -> dict[str, dict]:
    digest: dict[str, dict] = {}
    for stage in ("empathize", "define", "ideate", "prototype", "test"):
        traces = [t for t in model.model_traces if t.stage == stage]
        speakers = sorted(
            {e.speaker for e in model.evidence.values() if e.stage == stage and e.speaker}
        )
        agents = sorted(
            {
                e.agent
                for e in model.evidence.values()
                if e.stage == stage and e.agent and e.agent not in ("facilitator",)
            }
        )
        digest[stage] = {
            "personas": speakers,
            "systems": [*agents, "facilitator"],
            "calls": dict(Counter(t.routing_class for t in traces)),
            "models": sorted({t.model for t in traces}),
            "moves": sorted({m.move_id for m in model.moves if m.stage == stage and m.executed}),
            "process": STAGE_PROCESS[stage],
        }
    return digest


def _deliberation(model: DossierModel) -> tuple[list[dict], str | None, list[dict], list[dict]]:
    """(lens votes, skeptic challenge, kata moves, dissent) from the journal."""
    concept = next(
        (
            d
            for d in model.decisions.values()
            if d.question == "which concept advances to prototype"
        ),
        None,
    )
    votes = []
    dissent: list[dict] = []
    if concept:
        votes = [
            {"lens": pos.get("actor", "?"), "position": pos.get("position", "")}
            for pos in concept.positions
            if isinstance(pos, dict)
        ]
        dissent = [d for d in concept.dissent if isinstance(d, dict)]
    skeptic = next(
        (
            e.content
            for e in model.evidence.values()
            if e.speaker and "skeptic" in (e.speaker or "").lower()
        ),
        None,
    )
    moves = [
        {
            "move": mv.move_id,
            "stage": mv.stage or "-",
            "executed": mv.executed,
            "trigger": mv.trigger,
            "note": (mv.outcome if mv.executed else mv.reason) or "",
        }
        for mv in model.moves
    ]
    return votes, skeptic, moves, dissent


def _hill(session_dir: Path, model: DossierModel) -> dict:
    """WHO/WHAT/WOW lines and the 'We believe' hypothesis from prototype artifacts."""
    hill: dict = {}
    for artifact in model.artifacts:
        if artifact.kind not in ("concept_one_pager", "landing_copy", "storyboard", "demo_script"):
            continue
        path = session_dir / artifact.path
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip().lstrip("*-# ").strip()
            for key in ("WHO", "WHAT", "WOW"):
                prefix = f"{key}:"
                if stripped.upper().startswith(prefix) and key.lower() not in hill:
                    hill[key.lower()] = stripped[len(prefix) :].strip(" *")
            if "we believe" in stripped.lower() and "hypothesis" not in hill:
                hill["hypothesis"] = stripped
    return hill


def _next_actions(model: DossierModel, feature_results: list) -> list[str]:
    actions = []
    for r in feature_results:
        if r.get("verdict") == "broken" and r.get("finding"):
            actions.append(f"Fix ({r['feature']}): {r['finding']}")
    if model.recommendation:
        confidence = model.recommendation.resolution
        loop = next(
            (mv for mv in model.moves if mv.move_id == "loopback_proposal" and mv.executed), None
        )
        if loop and loop.outcome:
            actions.append(f"Address the test contradiction: {loop.outcome[:220]}")
        actions.append(
            f"Recommendation is '{confidence}': "
            + (
                "validate the supported assumptions with real users before building."
                if model.recommendation.requires_real_validation
                else "proceed per the recommendation."
            )
        )
    seen: set[str] = set()
    for item in model.negative_space.research_debt[:3]:
        if item.question not in seen:
            seen.add(item.question)
            actions.append(f"Real-user research: {item.question[:180]}")
    return actions[:8]


def _ui_feature_results(session_dir: Path, model: DossierModel) -> list:
    import json as _json

    for artifact in model.artifacts:
        if artifact.kind == "ui_feature_tests" and artifact.path.endswith(".json"):
            path = session_dir / artifact.path
            if path.exists():
                return _json.loads(path.read_text(encoding="utf-8"))
    return []


def _market_research(session_dir: Path, model: DossierModel) -> dict | None:
    import json as _json

    for artifact in model.artifacts:
        if artifact.kind == "market_research" and artifact.path.endswith(".json"):
            path = session_dir / artifact.path
            if path.exists():
                return _json.loads(path.read_text(encoding="utf-8"))
    return None


def _ui_review(session_dir: Path, model: DossierModel) -> str | None:
    artifact = next((a for a in model.artifacts if a.kind == "ui_review"), None)
    if artifact is None:
        return None
    path = session_dir / artifact.path
    return path.read_text(encoding="utf-8") if path.exists() else None


def _handoff_refusal(model: DossierModel) -> str | None:
    if model.recommendation and model.recommendation.resolution == "kill":
        return "the test recommendation is 'kill': a killed concept has no build handoff"
    return None


def _is_demo_session(session_dir: Path) -> bool:
    import json as _json

    journal = session_dir / "journal.jsonl"
    try:
        first = _json.loads(journal.read_text(encoding="utf-8").split("\n", 1)[0])
    except (OSError, ValueError):
        return False
    return bool(first.get("payload", {}).get("config", {}).get("demo"))


def build_context(session_dir: Path, model: DossierModel) -> ReportContext:
    per_model: dict[str, dict[str, int]] = {}
    for trace in model.model_traces:
        bucket = per_model.setdefault(
            trace.model,
            {"calls": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0},
        )
        bucket["calls"] += 1
        bucket["input"] += trace.usage.get("input_tokens", 0)
        bucket["output"] += trace.usage.get("output_tokens", 0)
        bucket["cache_read"] += trace.usage.get("cache_read_tokens", 0)
        bucket["cache_write"] += trace.usage.get("cache_write_tokens", 0)
    usage = []
    for name in sorted(per_model):
        b = per_model[name]
        usage.append(
            ModelUsageLine(
                model=name,
                calls=b["calls"],
                input_tokens=b["input"],
                output_tokens=b["output"],
                cache_read_tokens=b["cache_read"],
                cache_write_tokens=b["cache_write"],
                # The same pricing function the `costs` verb uses, so the two
                # surfaces cannot quote one session at two different numbers.
                cost_usd=call_cost_usd(name, row_usage(b)),
            )
        )

    spec_entries = _spec_entries(session_dir)
    register_counts = {"supported": 0, "contradicted": 0, "untested": 0}
    for a in model.assumptions.values():
        register_counts[a.score or "untested"] += 1

    dossier_paths = [
        p for p in ("dossier/dossier.md", "dossier/dossier.json") if (session_dir / p).exists()
    ]
    feature_results = _ui_feature_results(session_dir, model)
    lens_votes, skeptic, kata_moves, dissent = _deliberation(model)
    return ReportContext(
        session_dir=session_dir,
        model=model,
        usage=usage,
        total_cost_usd=sum(u.cost_usd for u in usage),
        demo=_is_demo_session(session_dir),
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
        opportunities=_ranked_opportunities(model),
        ui_review=_ui_review(session_dir, model),
        ui_screenshots=[a.path for a in model.artifacts if a.kind == "ui_screenshot"],
        stage_digest=_stage_digest(model),
        market_research=_market_research(session_dir, model),
        ui_feature_results=feature_results,
        lens_votes=lens_votes,
        skeptic_challenge=skeptic,
        kata_moves=kata_moves,
        dissent=dissent,
        next_actions=_next_actions(model, feature_results),
        hill=_hill(session_dir, model),
        dossier_paths=dossier_paths,
    )
