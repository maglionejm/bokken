"""Concept research: deep, authorized web research on the selected concept.

Runs once, after the concept decision and before assumption enumeration.
Two phases through the single model seam: a research-class call with the
provider's server-side web search (deep findings, cited URLs), then a
structuring call into the MarketResearch schema. Findings are `reported`
evidence - external sources, never observed. Without explicit authorization
(`allow_web_research: true` on the brief) the skip is journaled research
debt: a Dojo run never reaches the outside world silently.
"""

from __future__ import annotations

from bokken.journal.schema import content_hash
from bokken.stages.base import FACILITATOR, structured
from bokken.stages.schemas import MarketResearch


def prior_research(ctx) -> str:
    """The structured research already journaled, prompt-ready; '(none)' otherwise."""
    for event in ctx.store.events():
        if event.type == "artifact.generated" and event.payload.get("kind") == "market_research":
            path = ctx.store.session_dir / event.payload["path"]
            if path.suffix == ".json" and path.exists():
                return path.read_text(encoding="utf-8")
    return "(no concept research on file)"


def run_concept_research(ctx, router, *, concept: str, problem_statement: str) -> None:
    for event in ctx.store.events():
        if event.type == "artifact.generated" and event.payload.get("kind") == "market_research":
            return  # already researched; loop-backs do not re-crawl the web
        if event.type == "evidence.abstained" and str(event.payload.get("question", "")).startswith(
            "Concept research"
        ):
            return
    if not ctx.state.brief.get("allow_web_research"):
        ctx.store.append(
            type="evidence.abstained",
            stage="prototype",
            # No call was dispatched: this gap is the governance rule, not a model.
            actor=FACILITATOR,
            payload={
                "question": "Concept research on the live web",
                "gap": "the brief does not declare allow_web_research: true; deep "
                "market research on the selected concept was not performed",
            },
        )
        return

    deep = router.invoke(
        "research",
        "research/deep",
        stage="prototype",
        params={"concept": concept, "problem_statement": problem_statement},
        stream=True,
        max_tokens=32000,
        web_search=True,
    )
    if not deep.ok or not deep.text:
        ctx.store.append(
            type="evidence.abstained",
            stage="prototype",
            actor=deep.attribution.actor("concept-researcher"),
            payload={
                "question": "Concept research on the live web",
                "gap": f"research call failed: {deep.status} {deep.detail}",
            },
        )
        return
    research = structured(
        router,
        "research",
        "research/structure",
        MarketResearch,
        stage="prototype",
        params={"notes": deep.text},
    )
    if research is None:
        return

    refs = []
    researcher = research.actor("concept-researcher")
    for signal in research.data.market_signals:
        event = ctx.store.append(
            type="evidence.captured",
            stage="prototype",
            actor=researcher,
            payload={
                "content": signal.stat,
                "source": signal.source_url,
                "confidence_class": "reported",
            },
        )
        refs.append(event.id)
    for competitor in research.data.competitors:
        event = ctx.store.append(
            type="evidence.captured",
            stage="prototype",
            actor=researcher,
            payload={
                "content": f"{competitor.name}: {competitor.what}. Overlap: {competitor.overlap}",
                "source": competitor.url or "web research",
                "confidence_class": "reported",
            },
        )
        refs.append(event.id)

    research_dir = ctx.store.session_dir / "artifacts" / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    payload_json = research.data.model_dump_json(indent=2) + "\n"
    md_lines = ["# Concept research (web, authorized)", ""]
    if research.data.competitors:
        md_lines += ["## Competitors and prior art", ""]
        md_lines += [
            f"- **{c.name}** ({c.url or 'no url'}) — {c.what} Overlap: {c.overlap}"
            for c in research.data.competitors
        ] + [""]
    if research.data.market_signals:
        md_lines += ["## Market signals", ""]
        md_lines += [
            f"- {s.stat} (source: {s.source_url})" for s in research.data.market_signals
        ] + [""]
    for title, items in (
        ("Regulatory", research.data.regulatory),
        ("Pricing benchmarks", research.data.pricing_benchmarks),
        ("Differentiation risks", research.data.differentiation_risks),
        ("Open questions", research.data.open_questions),
    ):
        if items:
            md_lines += [f"## {title}", ""] + [f"- {i}" for i in items] + [""]
    content_md = "\n".join(md_lines)
    for name, content in (
        ("market_research.md", content_md),
        ("market_research.json", payload_json),
    ):
        (research_dir / name).write_text(content, encoding="utf-8")
        ctx.store.append(
            type="artifact.generated",
            stage="prototype",
            actor=researcher,  # rendered from what the structuring call returned
            payload={
                "path": f"artifacts/research/{name}",
                "kind": "market_research",
                "content_hash": content_hash(content),
            },
            refs=refs,
        )
