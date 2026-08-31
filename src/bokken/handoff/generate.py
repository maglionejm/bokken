"""Handoff generation: journal -> SpecPackage -> OpenSpec files, journaled."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bokken.dossier import build_model
from bokken.dossier.model import DossierModel
from bokken.handoff.render import (
    Exclusion,
    HandoffContext,
    HandoffFormatError,
    ValidationItem,
    normalize,
    render_package,
    validate_package,
)
from bokken.handoff.schema import SpecPackage
from bokken.journal import Actor, JournalStore, read_events
from bokken.stages.base import RouterFactory

HANDOFF_ACTOR = Actor(kind="system", name="handoff")
PACKAGE_KIND = "handoff_package"


class HandoffRefusedError(Exception):
    pass


class HandoffGenerationError(Exception):
    pass


def handoff_exists(session_dir: Path) -> bool:
    return any(
        e.type == "artifact.generated" and e.payload.get("kind") == PACKAGE_KIND
        for e in read_events(session_dir)
    )


def _context(model: DossierModel) -> HandoffContext:
    if model.concept is None:
        raise HandoffRefusedError(
            "no convergence decision in the journal; run the session through ideate first"
        )
    if model.recommendation is not None and model.recommendation.resolution == "kill":
        raise HandoffRefusedError(
            "the test recommendation is 'kill': a killed concept has no build handoff"
        )
    assumptions = list(model.assumptions.values())
    contradicted_indexes = {i for i, a in enumerate(assumptions) if a.score == "contradicted"}
    exclusions = [
        Exclusion(statement=a.statement, assumption_id=a.id, evidence_refs=[])
        for a in assumptions
        if a.score == "contradicted"
    ]
    validation_items = [
        ValidationItem(statement=a.statement, assumption_id=a.id, reason="untested")
        for a in assumptions
        if a.score in (None, "untested")
    ]
    if model.recommendation is not None and model.recommendation.requires_real_validation:
        validation_items.extend(
            ValidationItem(
                statement=a.statement,
                assumption_id=a.id,
                reason="requires_real_validation",
            )
            for a in assumptions
            if a.score == "supported"
        )
    return HandoffContext(
        change_id=f"build-mvp-{model.session_id}",
        session_name=model.name or model.session_id,
        mode=model.mode,
        problem_statement=model.problem_statement.resolution if model.problem_statement else "",
        concept=model.concept.resolution,
        assumption_ids=[a.id for a in assumptions],
        contradicted_indexes=contradicted_indexes,
        exclusions=exclusions,
        validation_items=validation_items,
        trace_ids={
            "problem_statement_decision": (
                model.problem_statement.id if model.problem_statement else None
            ),
            "concept_decision": model.concept.id,
            "recommendation_decision": (model.recommendation.id if model.recommendation else None),
        },
        dojo=model.mode == "dojo",
    )


def _prompt_params(model: DossierModel, ctx: HandoffContext) -> dict[str, str]:
    assumptions = list(model.assumptions.values())

    def listed(scores: tuple[str | None, ...]) -> str:
        lines = [f"{i}. {a.statement}" for i, a in enumerate(assumptions) if a.score in scores]
        return "\n".join(lines) or "(none)"

    return {
        "problem_statement": ctx.problem_statement or "(not recorded)",
        "concept": ctx.concept,
        "supported": listed(("supported",)),
        "untested": listed((None, "untested")),
        "contradicted": listed(("contradicted",)),
        "artifacts": ", ".join(a.kind for a in model.artifacts) or "(none)",
    }


def generate_handoff(session_dir: Path, router_factory: RouterFactory) -> dict:
    """Generate the handoff package. Returns {package_dir, change_id, capabilities}."""
    model = build_model(session_dir)
    ctx = _context(model)

    with JournalStore.open(session_dir) as store:
        router = router_factory(store)
        outcome = router.invoke(
            "cognition",
            "handoff/specify",
            stage="complete" if model.stage == "complete" else None,  # type: ignore[arg-type]
            params=_prompt_params(model, ctx),
            schema=SpecPackage,
        )
        if not outcome.ok or outcome.data is None:
            raise HandoffGenerationError(
                f"spec generation failed: {outcome.status} {outcome.detail}"
            )
        package = normalize(outcome.data, ctx)
        files = render_package(package, ctx)
        problems = validate_package(files)
        if problems:
            raise HandoffFormatError(
                "generated package is not OpenSpec-compliant: " + "; ".join(problems)
            )

        root = session_dir / "handoff"
        for relative, content in files.items():
            absolute = root / relative
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text(content, encoding="utf-8")
            store.append(
                type="artifact.generated",
                stage=None,
                actor=HANDOFF_ACTOR,
                payload={
                    "path": str(Path("handoff") / relative),
                    "kind": "handoff_spec",
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                },
            )
        store.append(
            type="artifact.generated",
            stage=None,
            actor=HANDOFF_ACTOR,
            payload={
                "path": f"handoff/openspec/changes/{ctx.change_id}",
                "kind": PACKAGE_KIND,
                "content_hash": hashlib.sha256("".join(sorted(files)).encode()).hexdigest(),
                "change_id": ctx.change_id,
                "capabilities": [c.name for c in package.capabilities],
            },
            refs=[i for i in ctx.trace_ids.values() if i],
        )
    return {
        "package_dir": str(root),
        "change_id": ctx.change_id,
        "capabilities": [c.name for c in package.capabilities],
    }
