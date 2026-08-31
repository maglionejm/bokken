import pytest

from bokken.journal.replay import (
    ArtifactRef,
    Assumption,
    Decision,
    Insight,
    OptionNode,
    SessionState,
)
from bokken.orchestrator import (
    IllegalTransitionError,
    can_exit,
    is_legal,
    is_loopback,
    legal_targets,
)


def test_forward_edges_are_legal() -> None:
    assert is_legal("intake", "empathize")
    assert is_legal("test", "complete")


def test_loopbacks_are_legal_and_flagged() -> None:
    for edge in [("test", "define"), ("test", "empathize"), ("define", "empathize")]:
        assert is_legal(*edge)
        assert is_loopback(*edge)


def test_illegal_edge_refused_with_legal_targets_named() -> None:
    assert not is_legal("empathize", "prototype")
    err = IllegalTransitionError("empathize", "prototype")
    assert "define" in str(err)


def test_legal_targets_from_test() -> None:
    assert legal_targets("test") == ["complete", "define", "empathize"]


BRIEF = {"target_segments": ["commuters", "operators"]}


def _insight(grounded: bool = True) -> Insight:
    return Insight(
        id="i1",
        kind="insight",
        statement="s",
        refs=["e1"] if grounded else [],
        ungrounded=not grounded,
    )


def _decision(stage: str) -> Decision:
    return Decision(
        id=f"d-{stage}",
        stage=stage,
        question="q",
        resolution="r",
        options=[],
        dissent=[],
        requires_real_validation=False,
    )


def test_intake_requires_brief() -> None:
    assert not can_exit("intake", SessionState()).ok
    assert can_exit("intake", SessionState(brief=BRIEF)).ok


def test_empathize_requires_per_segment_coverage() -> None:
    from bokken.journal.replay import EvidenceItem, ResearchDebtItem

    state = SessionState(brief=BRIEF)
    verdict = can_exit("empathize", state)
    assert not verdict.ok and len(verdict.unmet) >= 2

    state.evidence["e1"] = EvidenceItem(
        id="e1",
        stage="empathize",
        source="s",
        confidence_class="observed",
        speaker=None,
        segment="commuters",
    )
    verdict = can_exit("empathize", state)
    assert not verdict.ok
    assert any("operators" in u for u in verdict.unmet)

    state.research_debt.append(
        ResearchDebtItem(id="a1", stage="empathize", question="q", gap="g", segment="operators")
    )
    assert can_exit("empathize", state).ok


def test_define_requires_decision_and_grounded_insight() -> None:
    state = SessionState(brief=BRIEF)
    state.decisions["d"] = _decision("define")
    verdict = can_exit("define", state)
    assert not verdict.ok and "insight" in verdict.unmet[0]
    state.insights["i"] = _insight(grounded=True)
    assert can_exit("define", state).ok


def test_ideate_requires_survivor_and_convergence() -> None:
    state = SessionState(brief=BRIEF)
    state.options["o"] = OptionNode(
        id="o", summary="x", contributor="a", origin="created", parents=[], status="killed"
    )
    state.decisions["d"] = _decision("ideate")
    verdict = can_exit("ideate", state)
    assert not verdict.ok and "surviving" in verdict.unmet[0]
    state.options["o"].status = "alive"
    assert can_exit("ideate", state).ok


def test_prototype_requires_register_and_artifact() -> None:
    state = SessionState(brief=BRIEF)
    state.assumptions["a"] = Assumption(id="a", statement="s", impact="high", uncertainty="high")
    verdict = can_exit("prototype", state)
    assert not verdict.ok and "artifact" in verdict.unmet[0]
    state.artifacts.append(ArtifactRef(id="x", path="p", kind="k", content_hash="h", refs=["a"]))
    assert can_exit("prototype", state).ok


def test_test_requires_scored_register_and_recommendation() -> None:
    state = SessionState(brief=BRIEF)
    state.assumptions["a"] = Assumption(id="a", statement="s", impact="high", uncertainty="high")
    state.decisions["d"] = _decision("test")
    verdict = can_exit("test", state)
    assert not verdict.ok and "not yet scored" in verdict.unmet[0]
    state.assumptions["a"].score = "supported"
    assert can_exit("test", state).ok


def test_complete_has_no_forward_exit() -> None:
    assert not can_exit("complete", SessionState(brief=BRIEF)).ok


@pytest.mark.parametrize("stage", ["intake", "empathize", "define", "ideate", "prototype", "test"])
def test_verdicts_name_the_unmet_criterion(stage: str) -> None:
    verdict = can_exit(stage, SessionState())
    assert not verdict.ok
    assert all(u.startswith(f"{stage}:") for u in verdict.unmet)
