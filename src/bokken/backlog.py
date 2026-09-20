"""Validation backlog: a deterministic, replay-derived, no-model-call to-do list.

The backlog turns the assumption register and the research debt into one ranked,
exportable artifact answering "what do I go test next, and in what order". It is
pure derivation from the journal (no provider seam is touched): every number here
is a fold over the same events the dossier reads, so the backlog is honest,
deterministic, and free.

Honesty is carried, never invented: each item keeps the `confidence_class` of the
evidence that scored it, and a simulated-only backlog restates the dojo banner and
the requires-real-validation context so it is never read as validated fact. The
"what would flip the verdict" line states the register counts plainly rather than
asserting a threshold, because the kill/iterate/proceed recommendation is a
challenge-class judgement over the register (`stages/testing.py`), not a mechanical
cutoff.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from bokken.contract import BacklogItem, BacklogResult
from bokken.dossier.render import DOJO_BANNER
from bokken.journal import read_events, replay
from bokken.journal.replay import SessionState

# Ordinal weights for the impact x uncertainty ranking. The register records
# low/medium/high (see AssumptionRegistered in journal/schema.py); we rank on the
# product so a high-impact, high-uncertainty assumption outranks anything milder.
_LEVEL = {"low": 1, "medium": 2, "high": 3}

# Confidence classes, weakest to strongest as testimony. A backlog item inherits
# the strongest class among the evidence that scored it; with no scoring evidence
# it stays unscored (an untested assumption nobody has reacted to yet).
_STRENGTH = {"simulated": 0, "assumed": 1, "reported": 2, "observed": 3}


def _priority(impact: str, uncertainty: str) -> int:
    return _LEVEL.get(impact, 0) * _LEVEL.get(uncertainty, 0)


def _item_confidence(state: SessionState, score_refs: list[str], fallback: str) -> str:
    """The confidence class an item inherits from the evidence that scored it.

    Honesty never launders: an assumption scored only against simulated persona
    reactions is a simulated-confidence item. We take the strongest class among
    the scoring evidence; with none, we fall back to the session default so an
    unreacted assumption in a dojo run still reads as simulated framing.
    """
    classes = [state.evidence[r].confidence_class for r in score_refs if r in state.evidence]
    if not classes:
        return fallback
    return max(classes, key=lambda c: _STRENGTH.get(c, 0))


def build_backlog(session_dir: Path, name: str) -> BacklogResult:
    """Rank the untested and contradicted assumptions, fold in research debt.

    Supported assumptions are counted but never listed: they are not work left to
    do. Contradicted assumptions are listed as standing kill-or-iterate signals.
    """
    state = replay(read_events(session_dir))
    # A dojo run's synthetic contributions default to simulated framing; a founder
    # run's unscored assumptions have no observed testimony yet either, but the
    # dojo banner is what marks a backlog as not-yet-validated fact.
    fallback = "simulated" if state.mode == "dojo" else "assumed"

    supported = contradicted = untested = 0
    scored_items: list[tuple[int, int, BacklogItem]] = []
    for assumption in state.assumptions.values():
        score = assumption.score or "untested"
        if score == "supported":
            supported += 1
            continue  # supported assumptions are not work left to do
        if score == "contradicted":
            contradicted += 1
        else:
            score = "untested"
            untested += 1
        priority = _priority(assumption.impact, assumption.uncertainty)
        confidence = _item_confidence(state, assumption.score_refs, fallback)
        item = BacklogItem(
            rank=0,  # assigned after sorting
            kind="assumption",
            impact=assumption.impact,
            uncertainty=assumption.uncertainty,
            score=score,
            priority=priority,
            confidence_class=confidence,
            source=f"assumption {assumption.id}",
            statement=assumption.statement,
        )
        # Sort key: highest priority first, contradicted before untested at a tie
        # (a standing signal outranks a never-tested one), then journal order.
        contradicted_first = 0 if score == "contradicted" else 1
        scored_items.append((-priority, contradicted_first, item))

    scored_items.sort(key=lambda t: (t[0], t[1]))
    items = [item for _, _, item in scored_items]

    # Research debt: every open abstention is a backlog item. It carries the
    # abstention's confidence framing (a dojo run's research gaps are simulated
    # framing) and lands after the ranked assumptions — an open question has no
    # impact x uncertainty score to rank against.
    for debt in state.research_debt:
        items.append(
            BacklogItem(
                rank=0,
                kind="research_debt",
                confidence_class=fallback,
                source=f"research debt {debt.id}",
                statement=debt.question,
            )
        )

    for i, item in enumerate(items, start=1):
        item.rank = i

    research_debt = len(state.research_debt)
    flip = _flip_the_verdict(supported, contradicted, untested, research_debt)

    dojo = state.mode == "dojo"
    # A backlog is simulated-only when every listed item is simulated-confidence:
    # then the whole artifact must not be read as validated fact.
    simulated_only = bool(items) and all(it.confidence_class == "simulated" for it in items)
    requires_real_validation = dojo or simulated_only
    banner = DOJO_BANNER if (dojo or simulated_only) else None

    return BacklogResult(
        name=name,
        mode=state.mode,
        items=items,
        supported=supported,
        contradicted=contradicted,
        untested=untested,
        research_debt=research_debt,
        flip_the_verdict=flip,
        dojo_banner=dojo,
        requires_real_validation=requires_real_validation,
        simulated_only=simulated_only,
        banner=banner,
    )


def _flip_the_verdict(supported: int, contradicted: int, untested: int, research_debt: int) -> str:
    """State the register counts and the gap plainly — no invented cutoff.

    The kill/iterate/proceed recommendation is a challenge-class judgement over
    the register text (stages/testing.py `_recommend`), so this line does not
    assert a threshold. It reports what is on the register and what would have to
    move: how many untested items remain to resolve, and that any contradicted
    item is a standing kill-or-iterate signal.
    """
    if contradicted == 0 and untested == 0 and research_debt == 0:
        return f"Register: {supported} supported, 0 contradicted, 0 untested. Nothing left to test."
    parts = [f"Register: {supported} supported, {contradicted} contradicted, {untested} untested."]
    if untested:
        noun = "assumption" if untested == 1 else "assumptions"
        parts.append(f"To flip the verdict, {untested} untested {noun} would have to resolve")
        if research_debt:
            gap_noun = "gap" if research_debt == 1 else "gaps"
            parts[-1] += f" and {research_debt} open research {gap_noun} would have to close"
        parts[-1] += "."
    elif research_debt:
        gap_noun = "gap" if research_debt == 1 else "gaps"
        parts.append(
            f"To flip the verdict, {research_debt} open research {gap_noun} would have to close."
        )
    if contradicted:
        signal = "item is" if contradicted == 1 else "items are"
        parts.append(
            f"Any of the {contradicted} contradicted {signal} a standing kill-or-iterate signal."
        )
    return " ".join(parts)


def _rows(result: BacklogResult) -> list[list[str]]:
    return [
        [
            str(it.rank),
            it.kind,
            it.impact or "",
            it.uncertainty or "",
            it.score or "",
            it.confidence_class,
            it.source,
            it.statement,
        ]
        for it in result.items
    ]


_HEADER = [
    "rank",
    "kind",
    "impact",
    "uncertainty",
    "score",
    "confidence_class",
    "source",
    "statement",
]


def to_csv(result: BacklogResult) -> str:
    """Issue-tracker-ready CSV: one header row then one row per ranked item."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_HEADER)
    for row in _rows(result):
        writer.writerow(row)
    return buffer.getvalue()


def to_markdown(result: BacklogResult) -> str:
    """Issue-tracker checklist in markdown: a task list of the ranked items."""
    lines: list[str] = [f"# Validation backlog - {result.name}", ""]
    if result.banner:
        lines += [f"> {result.banner.lstrip('> ')}", ""]
    lines += [result.flip_the_verdict, ""]
    if not result.items:
        lines.append("- [x] Nothing left to test.")
        return "\n".join(lines) + "\n"
    for it in result.items:
        detail = _md_detail(it)
        lines.append(f"- [ ] **#{it.rank}** {_flat(it.statement)}{detail}")
    return "\n".join(lines) + "\n"


def _md_detail(it: BacklogItem) -> str:
    tags = [it.kind]
    if it.kind == "assumption":
        tags.append(f"impact {it.impact}")
        tags.append(f"uncertainty {it.uncertainty}")
        if it.score:
            tags.append(it.score)
    tags.append(it.confidence_class)
    tags.append(it.source)
    return f" ({', '.join(tags)})"


def _flat(s: str) -> str:
    """Collapse free text onto one line so a checklist row stays one item."""
    return " ".join((s or "").split())
