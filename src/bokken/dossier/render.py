"""Renderers over the DossierModel. Labels live on the model; renderers must print them."""

from __future__ import annotations

from bokken.dossier.model import EXCLUDED_ARTIFACT_KINDS, DecisionNode, DossierModel

DOJO_BANNER = (
    "> SIMULATED RUN. This dossier was produced by an autonomous run against a "
    "governed synthetic persona panel. All persona contributions are simulated and "
    "evidence-bounded. Decisions flagged below require validation with real users "
    "before they are acted on."
)


def _flat(s: str | None) -> str:
    """Collapse journal free text onto one line so it cannot inject markdown
    structure (an embedded "\\n## " would otherwise become a real heading)."""
    return " ".join((s or "").split())


def _label(synthetic: bool, flagged: bool = False) -> str:
    parts = []
    if synthetic:
        parts.append("[synthetic]")
    if flagged:
        parts.append("[requires real validation]")
    return (" " + " ".join(parts)) if parts else ""


def _decision_line(node: DecisionNode | None, fallback: str) -> str:
    if node is None:
        return f"_{fallback}_"
    label = _label(False, node.requires_real_validation)
    return f"{_flat(node.resolution)}{label} (decision `{node.id}`)"


def render_markdown(model: DossierModel, generated_at: str) -> str:
    lines: list[str] = [f"# Session Dossier - {_flat(model.name)}", ""]
    if model.dojo_banner:
        lines += [DOJO_BANNER, ""]
    lines += [
        f"Mode: {model.mode}. Status: {model.status} (reached stage: {model.stage}). "
        f"Generated: {generated_at}.",
        "",
        "## Part A - Outcomes",
        "",
        f"**Problem statement.** {_decision_line(model.problem_statement, 'not yet selected')}",
        "",
        f"**Concept advanced.** {_decision_line(model.concept, 'not yet selected')}",
        "",
    ]
    prototype_artifacts = [a for a in model.artifacts if a.kind not in EXCLUDED_ARTIFACT_KINDS]
    if prototype_artifacts:
        lines.append("**Prototype artifacts.**")
        for artifact in prototype_artifacts:
            line = f"- `{artifact.path}` ({artifact.kind}, sha256 `{artifact.content_hash[:12]}`)"
            if artifact.assumption_ids:
                ids = ", ".join(f"`{a}`" for a in artifact.assumption_ids)
                line += f", tests assumptions: {ids}"
            lines.append(line)
        lines.append("")
    if model.assumptions:
        lines.append("**Assumption register.**")
        for a in model.assumptions.values():
            score = a.score or "untested"
            lines.append(
                f"- [{score}] {_flat(a.statement)} (impact {a.impact}, "
                f"uncertainty {a.uncertainty}, `{a.id}`)"
            )
        lines.append("")
    lines.append(
        f"**Recommendation.** {_decision_line(model.recommendation, 'no test recommendation yet')}"
    )
    lines.append("")

    lines += ["## Part B - Process narrative", ""]
    lines.append("**The arc.**")
    for t in model.transitions:
        kind = "loop-back" if t.loopback else "forward"
        refs = f" (refs: {', '.join(f'`{r}`' for r in t.refs)})" if t.refs else ""
        lines.append(f"- {t.from_stage} -> {t.to_stage} ({kind}): {_flat(t.condition)}{refs}")
    lines.append("")
    if model.pivotal_moments:
        lines.append("**Pivotal moments.**")
        for moment in model.pivotal_moments:
            refs = f" (refs: {', '.join(f'`{r}`' for r in moment.refs)})" if moment.refs else ""
            lines.append(f"- {_flat(moment.description)}{refs}")
        lines.append("")
    lines.append("**Options seriously considered and why the losers lost.**")
    for decision in model.decisions.values():
        if decision.question in ("convergence criteria", "contamination firewall check"):
            continue
        lines.append(
            f"- {_flat(decision.question)} (decision `{decision.id}`, by {decision.actor}):"
        )
        for option in decision.options:
            lines.append(f"  - {_flat(option)}")
        lines.append(f"  - resolved: {_flat(decision.resolution)}")
        for dissent in decision.dissent:
            lines.append(
                f"  - dissent on record ({_flat(dissent.get('actor', 'unknown'))}): "
                f"{_flat(dissent.get('reservation', ''))}"
            )
    lines.append("")
    executed = [m for m in model.moves if m.executed]
    if executed:
        lines.append("**Where the facilitation intervened.**")
        for move in executed:
            lines.append(f"- {move.move_id} in {move.stage}: {_flat(move.trigger)} (`{move.id}`)")
        lines.append("")

    lines += ["## Honesty", ""]
    synthetic_count = sum(1 for e in model.evidence.values() if e.synthetic)
    lines.append(
        f"Evidence base: {len(model.evidence)} item(s), of which {synthetic_count} "
        "synthetic [synthetic items are labeled at record level in Part C]."
    )
    flagged = [d for d in model.decisions.values() if d.requires_real_validation]
    if flagged:
        lines.append("Decisions requiring real-user validation:")
        for decision in flagged:
            lines.append(
                f"- {_flat(decision.question)} -> {_flat(decision.resolution)} (`{decision.id}`)"
            )
    lines.append("")
    lines.append("**What this run did not do (negative space).**")
    ns = model.negative_space
    if ns.stages_not_reached:
        lines.append(f"- stages not reached: {', '.join(ns.stages_not_reached)}")
    for debt in ns.research_debt:
        lines.append(f"- open research debt: {_flat(debt.question)} ({_flat(debt.gap)})")
    for move in ns.suppressed_moves:
        lines.append(f"- suppressed move: {move.move_id} ({_flat(move.reason)})")
    for reason in ns.gates_rejected:
        lines.append(f"- gate rejected: {_flat(reason)}")
    if not any((ns.stages_not_reached, ns.research_debt, ns.suppressed_moves, ns.gates_rejected)):
        lines.append("- nothing skipped: all stages ran, no open research debt on record")
    lines.append("")
    lines.append("Part C (the full evidence graph) is machine-readable in `dossier.json`.")
    return "\n".join(lines) + "\n"


def render_json(model: DossierModel, generated_at: str) -> str:
    document = model.model_dump(mode="json")
    document["generated_at"] = generated_at
    import json

    return json.dumps(document, sort_keys=True, indent=2) + "\n"
