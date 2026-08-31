from pathlib import Path

import pytest

from bokken.journal import Actor, JournalStore

HUMAN = Actor(kind="human", name="founder")
AGENT = Actor(kind="agent", name="facilitator", model="claude-opus-4-8")
SYSTEM = Actor(kind="system", name="orchestrator")


def persona(persona_id: str = "p-1") -> Actor:
    return Actor(kind="agent", name="panelist", model="claude-opus-4-8", persona_id=persona_id)


BRIEF = {
    "problem_space": "sustainable urban mobility",
    "constraints": ["budget under 10k"],
    "target_segments": ["commuters"],
    "success_criteria": ["validated demand"],
    "risk_tolerance": "medium",
}


def created_payload(name: str = "test-session", mode: str = "founder") -> dict:
    return {"name": name, "mode": mode, "brief": BRIEF, "config": {}}


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions" / "test-session"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def store(session_dir: Path):
    with JournalStore.open(session_dir) as s:
        s.append(type="session.created", stage="intake", actor=SYSTEM, payload=created_payload())
        yield s
