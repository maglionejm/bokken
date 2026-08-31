import pytest

from bokken.journal import Actor
from bokken.orchestrator import (
    Runner,
    StageContext,
    StageOutcome,
    StalledStageError,
    create_session,
)
from tests.journal.conftest import BRIEF

AGENT = Actor(kind="agent", name="spinner", model="fake")


class SpinningEngine:
    """Appends events forever but never satisfies define's exit criteria."""

    def run(self, ctx: StageContext) -> StageOutcome | None:
        ctx.store.append(
            type="interpretation.derived",
            stage="empathize",
            actor=AGENT,
            payload={"kind": "insight", "statement": "ungrounded hunch", "ungrounded": True},
        )
        return None


def test_progressless_engine_raises_instead_of_looping(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path))
    session_dir = create_session("spin", brief=BRIEF, mode="founder")
    runner = Runner(session_dir, engines={"empathize": SpinningEngine()})
    with pytest.raises(StalledStageError, match="without meeting the exit criteria"):
        runner.run()
