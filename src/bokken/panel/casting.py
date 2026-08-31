"""Panel casting: seeded, documented sampling of personas plus mandatory role agents."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bokken.journal import Actor, Event, JournalStore, Stage

PanelKind = Literal["interview", "ideation", "test"]
Role = Literal["segment", "skeptic", "feasibility", "viability"]

ROLE_AGENTS: tuple[tuple[Role, str], ...] = (
    ("skeptic", "challenges weak claims and premature consensus"),
    ("feasibility", "assesses whether the concept can actually be built and operated"),
    ("viability", "assesses whether the concept can sustain itself economically"),
)

# Documented sampling axes for segment personas (reviewed as code, per design).
SAMPLING_AXES: dict[str, tuple[str, ...]] = {
    "life_context": ("student", "early career", "parent of young children", "near retirement"),
    "attitude_to_change": ("early adopter", "pragmatist", "conservative"),
    "resource_level": ("tight budget", "comfortable", "well resourced"),
}

OCEAN_TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


class CastingError(Exception):
    pass


class Persona(BaseModel):
    model_config = ConfigDict(frozen=True)

    persona_id: str
    name: str
    role: Role
    segment: str | None
    profile: dict[str, str] = Field(default_factory=dict)
    ocean: dict[str, float] = Field(default_factory=dict)
    grounding_scope: list[str] = Field(default_factory=list)

    def actor(self, model: str = "claude-opus-4-8") -> Actor:
        return Actor(kind="agent", name=self.name, model=model, persona_id=self.persona_id)


def _persona_id(role: str, segment: str | None, profile: dict, ocean: dict, seed: int) -> str:
    material = json.dumps(
        {"role": role, "segment": segment, "profile": profile, "ocean": ocean, "seed": seed},
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def cast_panel(
    *,
    brief: dict,
    size: int,
    seed: int,
    grounding_sources: list[str] | None = None,
) -> list[Persona]:
    """Deterministically cast a panel: role agents + sampled segment personas."""
    segments = list(brief.get("target_segments", []))
    minimum = len(ROLE_AGENTS) + len(segments)
    if size < minimum:
        raise CastingError(
            f"panel size {size} cannot cover {len(segments)} segment(s) plus "
            f"{len(ROLE_AGENTS)} role agents (minimum {minimum})"
        )
    rng = random.Random(seed)
    scope = grounding_sources or []
    personas: list[Persona] = []

    for i, (role, intent) in enumerate(ROLE_AGENTS):
        ocean = {t: round(rng.uniform(0.2, 0.8), 3) for t in OCEAN_TRAITS}
        profile = {"intent": intent}
        personas.append(
            Persona(
                persona_id=_persona_id(role, None, profile, ocean, seed + i),
                name=f"{role}-agent",
                role=role,
                segment=None,
                profile=profile,
                ocean=ocean,
                grounding_scope=scope,
            )
        )

    n_segment_personas = size - len(ROLE_AGENTS)
    for i in range(n_segment_personas):
        segment = segments[i % len(segments)] if segments else None
        profile = {axis: rng.choice(values) for axis, values in SAMPLING_AXES.items()}
        ocean = {t: round(rng.uniform(0.05, 0.95), 3) for t in OCEAN_TRAITS}
        personas.append(
            Persona(
                persona_id=_persona_id("segment", segment, profile, ocean, seed + 100 + i),
                name=f"{segment or 'general'}-{i + 1}",
                role="segment",
                segment=segment,
                profile=profile,
                ocean=ocean,
                grounding_scope=scope,
            )
        )
    return personas


def journal_manifest(
    store: JournalStore,
    *,
    personas: list[Persona],
    panel_kind: PanelKind,
    seed: int,
    stage: Stage,
) -> Event:
    """Persist the casting manifest to disk and journal it before any panel content."""
    manifest = {
        "panel_kind": panel_kind,
        "seed": seed,
        "personas": [p.model_dump() for p in personas],
    }
    content = json.dumps(manifest, sort_keys=True, indent=2)
    path = Path("artifacts") / "panel" / f"{panel_kind}-manifest-{seed}.json"
    absolute = store.session_dir / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(content, encoding="utf-8")
    return store.append(
        type="artifact.generated",
        stage=stage,
        actor=Actor(kind="system", name="panel"),
        payload={
            "path": str(path),
            "kind": "panel_manifest",
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "panel_kind": panel_kind,
            "seed": seed,
            "persona_ids": [p.persona_id for p in personas],
        },
    )
