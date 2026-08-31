"""Panel governance enforced in code: firewall, anti-sycophancy, labeling."""

from __future__ import annotations

from typing import Any

from bokken.journal import Actor, Event, JournalStore, SessionState, Stage, replay
from bokken.panel.casting import Persona

PANEL_ACTOR = Actor(kind="system", name="panel")

CRITERIA_QUESTION = "convergence criteria"
FIREWALL_QUESTION = "contamination firewall check"

# Keys whose presence marks sponsor preference; stripped from persona-visible material.
_PREFERENCE_KEYS = frozenset(
    {"preferred", "preferred_answer", "sponsor_hypothesis", "sponsor_preference", "desired_outcome"}
)

# Config keys that would weaken synthetic labeling; always rejected.
_FORBIDDEN_CONFIG_KEYS = frozenset(
    {"label_synthetic", "disable_synthetic_labels", "suppress_validation_flags"}
)


class ContaminationError(Exception):
    pass


class CriteriaFrozenError(Exception):
    pass


class ConvergenceBlockedError(Exception):
    pass


class PanelConfigError(Exception):
    pass


def validate_panel_config(config: dict[str, Any]) -> None:
    """Synthetic labeling and validation flags are not configurable. Ever."""
    bad = _FORBIDDEN_CONFIG_KEYS & set(config.get("panel", config))
    if bad:
        raise PanelConfigError(
            f"invalid configuration {sorted(bad)}: synthetic labeling and validation "
            "flags cannot be disabled"
        )


def strip_preferences(material: Any) -> Any:
    """Recursively remove sponsor-preference markers from persona-visible material."""
    if isinstance(material, dict):
        return {k: strip_preferences(v) for k, v in material.items() if k not in _PREFERENCE_KEYS}
    if isinstance(material, list):
        return [strip_preferences(v) for v in material]
    return material


def freeze_criteria(store: JournalStore, *, criteria: list[str], stage: Stage = "ideate") -> Event:
    """Fix convergence criteria before divergence begins. Immutable afterwards."""
    state = replay(store.events())
    if frozen_criteria(state) is not None:
        raise CriteriaFrozenError("convergence criteria are already frozen for this run")
    if state.options:
        raise CriteriaFrozenError("criteria must be frozen before any option exists")
    return store.append(
        type="decision.recorded",
        stage=stage,
        actor=PANEL_ACTOR,
        payload={
            "question": CRITERIA_QUESTION,
            "options": criteria,
            "criteria": ["fixed before divergence; immutable for the run"],
            "resolution": "frozen",
            "dissent": [],
        },
    )


def frozen_criteria(state: SessionState) -> list[str] | None:
    for decision in state.decisions.values():
        if decision.question == CRITERIA_QUESTION:
            return decision.options
    return None


def check_firewall(store: JournalStore, test_personas: list[Persona]) -> Event:
    """Verify the test panel shares no persona with any prior panel; journal the check.

    Raises ContaminationError (after journaling the refusal) on any overlap,
    before any persona sees the prototype.
    """
    prior_ids: set[str] = set()
    for event in store.events():
        if (
            event.type == "artifact.generated"
            and event.payload.get("kind") == "panel_manifest"
            and event.payload.get("panel_kind") in ("interview", "ideation")
        ):
            prior_ids.update(event.payload.get("persona_ids", []))
    test_ids = {p.persona_id for p in test_personas}
    overlap = sorted(prior_ids & test_ids)
    resolution = "disjoint" if not overlap else f"refused: persona overlap {overlap}"
    event = store.append(
        type="decision.recorded",
        stage="test",
        actor=PANEL_ACTOR,
        payload={
            "question": FIREWALL_QUESTION,
            "options": sorted(test_ids),
            "criteria": ["zero persona overlap with interview/ideation panels"],
            "resolution": resolution,
            "dissent": [],
        },
    )
    if overlap:
        raise ContaminationError(
            f"test panel shares {len(overlap)} persona(s) with a prior panel: {overlap}"
        )
    return event


def skeptic_has_challenged(state: SessionState, skeptic_ids: set[str]) -> bool:
    """True when the skeptic has at least one on-record contribution."""
    for item in state.evidence.values():
        if item.source.removeprefix("persona:") in skeptic_ids:
            return True
    return any(
        any(d.get("actor") in skeptic_ids for d in decision.dissent)
        for decision in state.decisions.values()
    )


def require_skeptic_challenge(state: SessionState, skeptic_ids: set[str]) -> None:
    if not skeptic_has_challenged(state, skeptic_ids):
        raise ConvergenceBlockedError(
            "convergence is blocked: the skeptic has no on-record challenge yet"
        )


def requires_real_validation(state: SessionState, refs: list[str]) -> bool:
    """Does a decision resting on these refs inherit the validation flag?

    Walks refs through insights to evidence; simulated or assumed grounding
    anywhere in the chain flags the decision.
    """
    pending = list(refs)
    seen: set[str] = set()
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        evidence = state.evidence.get(ref)
        if evidence is not None and evidence.confidence_class in ("simulated", "assumed"):
            return True
        insight = state.insights.get(ref)
        if insight is not None:
            if insight.ungrounded:
                return True
            pending.extend(insight.refs)
    return False
