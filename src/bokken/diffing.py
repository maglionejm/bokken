"""Cross-run diff: what moved between two finalized runs of the same product.

Pure derivation. Both surfaces (the CLI table and `--json`) consume the one
structure built here, so they never disagree. No model calls, no journal
writes, no session mutation: the diff builds the shared dossier model
(`dossier.model.build_model`) for each session and compares the four things that
move run-to-run — the Ulwick opportunity ranking, the assumption scores, the
code-exploration current capabilities, and the recommendation verdict.

Honesty is copied, never re-derived: every row records which run it came from
and carries the confidence class the source model already assigned. An
opportunity grounded only in `simulated` material stays `simulated` in the diff;
an assumption tested by real testimony reads as such. The diff never re-grounds
or relabels anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bokken.dossier.model import DossierModel, InsightNode, build_model
from bokken.library import _product_key


class DiffRefused(Exception):
    """A precondition failed: unfinalized session, or not the same product.

    The CLI maps this to exit code 2 (never a silent empty diff).
    """


@dataclass(frozen=True)
class OpportunityDelta:
    run: str  # "both" | "new" | "old"
    statement: str
    confidence_class: str
    old_score: float | None = None
    new_score: float | None = None
    score_delta: float | None = None
    old_band: str | None = None
    new_band: str | None = None


@dataclass(frozen=True)
class AssumptionFlip:
    run: str  # "both" | "new" | "old"
    statement: str
    confidence_class: str
    old_score: str | None = None
    new_score: str | None = None


@dataclass(frozen=True)
class CapabilityChange:
    run: str  # "both" | "new" | "old"
    statement: str
    confidence_class: str
    change: str  # "added" | "removed" | "changed"


@dataclass(frozen=True)
class VerdictChange:
    old_verdict: str | None
    new_verdict: str | None
    changed: bool
    old_confidence_class: str
    new_confidence_class: str


@dataclass(frozen=True)
class DiffData:
    old_session: str
    new_session: str
    product: str
    opportunities: list[OpportunityDelta] = field(default_factory=list)
    assumptions: list[AssumptionFlip] = field(default_factory=list)
    capabilities: list[CapabilityChange] = field(default_factory=list)
    verdict: VerdictChange | None = None


def _insight_confidence(node: InsightNode) -> str:
    """Copy the honesty label the model already carries onto a diff row.

    The model marks an insight `synthetic` when it is grounded only in
    simulated/assumed material (or is ungrounded). We report that as
    `simulated`, and grounded material as `grounded` — no re-derivation.
    """
    return "simulated" if node.synthetic else "grounded"


def _run_confidence(model: DossierModel) -> str:
    """A whole-run honesty label, copied from the model, for rows that summarize
    material without a per-insight confidence class (assumptions, the verdict).

    A dojo run is synthetic throughout; a founder run reads as real testimony.
    """
    return "simulated" if model.dojo_banner else "reported"


def _opportunities(model: DossierModel) -> dict[str, InsightNode]:
    # Keyed by statement: the diff matches Ulwick outcomes across runs by their
    # statement text, as the spec requires. Later insertions win a duplicate.
    return {i.statement: i for i in model.insights.values() if i.kind == "opportunity"}


def _capabilities(model: DossierModel) -> dict[str, InsightNode]:
    return {i.statement: i for i in model.insights.values() if i.kind == "current_capability"}


def _verdict(model: DossierModel) -> str | None:
    return model.recommendation.resolution if model.recommendation is not None else None


def _diff_opportunities(old: DossierModel, new: DossierModel) -> list[OpportunityDelta]:
    old_ops = _opportunities(old)
    new_ops = _opportunities(new)
    rows: list[OpportunityDelta] = []
    for statement, new_node in new_ops.items():
        if statement in old_ops:
            old_node = old_ops[statement]
            delta: float | None = None
            if old_node.score is not None and new_node.score is not None:
                delta = round(new_node.score - old_node.score, 6)
            rows.append(
                OpportunityDelta(
                    run="both",
                    statement=statement,
                    # A "both" row summarizes the new run's material; carry its
                    # class unchanged. (It is synthetic iff both are.)
                    confidence_class=_insight_confidence(new_node),
                    old_score=old_node.score,
                    new_score=new_node.score,
                    score_delta=delta,
                    old_band=old_node.band,
                    new_band=new_node.band,
                )
            )
        else:
            rows.append(
                OpportunityDelta(
                    run="new",
                    statement=statement,
                    confidence_class=_insight_confidence(new_node),
                    new_score=new_node.score,
                    new_band=new_node.band,
                )
            )
    for statement, old_node in old_ops.items():
        if statement not in new_ops:
            rows.append(
                OpportunityDelta(
                    run="old",
                    statement=statement,
                    confidence_class=_insight_confidence(old_node),
                    old_score=old_node.score,
                    old_band=old_node.band,
                )
            )
    return rows


def _diff_assumptions(old: DossierModel, new: DossierModel) -> list[AssumptionFlip]:
    old_by = {a.statement: a for a in old.assumptions.values()}
    new_by = {a.statement: a for a in new.assumptions.values()}
    old_conf = _run_confidence(old)
    new_conf = _run_confidence(new)
    rows: list[AssumptionFlip] = []
    for statement, new_a in new_by.items():
        if statement in old_by:
            old_a = old_by[statement]
            if (old_a.score or "untested") != (new_a.score or "untested"):
                # Only score changes are flips; an unchanged assumption is silent.
                rows.append(
                    AssumptionFlip(
                        run="both",
                        statement=statement,
                        confidence_class=new_conf,
                        old_score=old_a.score or "untested",
                        new_score=new_a.score or "untested",
                    )
                )
        else:
            rows.append(
                AssumptionFlip(
                    run="new",
                    statement=statement,
                    confidence_class=new_conf,
                    new_score=new_a.score or "untested",
                )
            )
    for statement, old_a in old_by.items():
        if statement not in new_by:
            rows.append(
                AssumptionFlip(
                    run="old",
                    statement=statement,
                    confidence_class=old_conf,
                    old_score=old_a.score or "untested",
                )
            )
    return rows


def _diff_capabilities(old: DossierModel, new: DossierModel) -> list[CapabilityChange]:
    old_caps = _capabilities(old)
    new_caps = _capabilities(new)
    rows: list[CapabilityChange] = []
    for statement, new_node in new_caps.items():
        if statement not in old_caps:
            rows.append(
                CapabilityChange(
                    run="new",
                    statement=statement,
                    confidence_class=_insight_confidence(new_node),
                    change="added",
                )
            )
        elif old_caps[statement].synthetic != new_node.synthetic:
            # Same capability text, different honesty label between runs: a
            # change worth surfacing (e.g. a founder later disputed one).
            rows.append(
                CapabilityChange(
                    run="both",
                    statement=statement,
                    confidence_class=_insight_confidence(new_node),
                    change="changed",
                )
            )
    for statement, old_node in old_caps.items():
        if statement not in new_caps:
            rows.append(
                CapabilityChange(
                    run="old",
                    statement=statement,
                    confidence_class=_insight_confidence(old_node),
                    change="removed",
                )
            )
    return rows


def diff_sessions(old_dir: Path, new_dir: Path) -> DiffData:
    """Build the cross-run diff for two finalized runs of the same product.

    Raises `DiffRefused` (mapped to exit 2 by the CLI) when either session is
    not finalized, or when the two sessions are not the same product — product
    identity being the library product key (`inputs.repo`, else the brief
    `problem_space`).
    """
    old = build_model(old_dir)
    new = build_model(new_dir)

    if old.status != "complete":
        raise DiffRefused(
            f"session '{old.name}' is not finalized (stage {old.stage}); "
            f"finalize it by completing the run with `bokken run {old.name}`"
        )
    if new.status != "complete":
        raise DiffRefused(
            f"session '{new.name}' is not finalized (stage {new.stage}); "
            f"finalize it by completing the run with `bokken run {new.name}`"
        )

    old_product = _product_key(old.brief)
    new_product = _product_key(new.brief)
    if old_product != new_product:
        raise DiffRefused(
            "sessions are not the same product: "
            f"'{old.name}' is {old_product!r} but '{new.name}' is {new_product!r}; "
            "diff compares two runs of one product"
        )

    old_verdict = _verdict(old)
    new_verdict = _verdict(new)
    verdict = VerdictChange(
        old_verdict=old_verdict,
        new_verdict=new_verdict,
        changed=old_verdict != new_verdict,
        old_confidence_class=_run_confidence(old),
        new_confidence_class=_run_confidence(new),
    )

    return DiffData(
        old_session=old.name,
        new_session=new.name,
        product=old_product,
        opportunities=_diff_opportunities(old, new),
        assumptions=_diff_assumptions(old, new),
        capabilities=_diff_capabilities(old, new),
        verdict=verdict,
    )
