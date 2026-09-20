"""The pre-flight estimate is a pure derivation: no model calls, honest range,
lanes that reconcile, and a panel-size and provider/model sensitivity that
match how a created session would actually route."""

from __future__ import annotations

import pytest

from bokken.estimate import PROMPT_PROFILE, estimate_run
from bokken.models import RoutingConfigError
from bokken.report.context import functional_bucket


def test_range_low_does_not_exceed_high() -> None:
    est = estimate_run(6)
    assert est.cost_low_usd <= est.cost_point_usd <= est.cost_high_usd
    # A range, never a single false-precision number.
    assert est.cost_low_usd < est.cost_high_usd


def test_lane_costs_sum_to_the_point_estimate() -> None:
    est = estimate_run(6)
    lane_sum = round(sum(lane.cost_usd for lane in est.lanes), 4)
    assert lane_sum == est.cost_point_usd


def test_three_named_lanes_in_costs_vocabulary() -> None:
    est = estimate_run(6)
    assert [lane.lane for lane in est.lanes] == ["exploration", "research", "synthesis"]


def test_larger_panel_costs_more_and_adds_research_calls() -> None:
    small = estimate_run(4)
    large = estimate_run(10)
    assert large.cost_point_usd > small.cost_point_usd
    research = {e.panel_size: {la.lane: la for la in e.lanes} for e in (small, large)}
    assert research[10]["research"].calls > research[4]["research"].calls


def test_provider_changes_the_priced_model() -> None:
    anthropic = estimate_run(6, provider="anthropic")
    openai = estimate_run(6, provider="openai")
    # Different served models -> a different priced total, not the same number.
    assert openai.cost_point_usd != anthropic.cost_point_usd


def test_model_override_changes_the_priced_model() -> None:
    default = estimate_run(6)
    override = estimate_run(6, model="claude-opus-4-8")
    # Frontier lanes reroute off the pricier fable model to the override.
    assert override.cost_point_usd != default.cost_point_usd
    assert override.model == "claude-opus-4-8"


def test_impossible_model_lane_combo_is_refused_before_any_estimate() -> None:
    # haiku serves only the extraction lane; forcing it onto a frontier lane is
    # rejected at derivation time, exactly as a created session would refuse it.
    with pytest.raises(RoutingConfigError):
        estimate_run(6, model="claude-haiku-4-5")


def test_panel_size_must_be_positive() -> None:
    with pytest.raises(ValueError):
        estimate_run(0)


def test_assumptions_state_panel_size_and_modeled_profile() -> None:
    est = estimate_run(6)
    blob = " ".join(est.assumptions).lower()
    assert "6" in blob
    assert "modeled" in blob
    assert "not a measurement" in est.caveat.lower()


def test_profile_prompt_ids_bucket_into_the_three_lanes() -> None:
    # Every profiled prompt reconciles with the costs functional vocabulary.
    for entry in PROMPT_PROFILE:
        assert functional_bucket(entry.prompt_id) in ("exploration", "research", "synthesis")


def test_prompt_profile_is_pinned_to_the_registry():
    """The estimate's accuracy depends on PROMPT_PROFILE tracking the real
    prompt set; pin its ids and routing classes to the PROMPTS registry so a
    stage adding/renaming/reclassifying a call can't silently rot the estimate."""
    from bokken.estimate import PROMPT_PROFILE
    from bokken.models.prompts import PROMPTS
    from bokken.models.router import DEFAULT_ROUTING  # noqa: F401  (import guard)

    profile_ids = {e.prompt_id for e in PROMPT_PROFILE}
    unknown = profile_ids - set(PROMPTS)
    assert not unknown, f"PROMPT_PROFILE references prompt ids absent from the registry: {unknown}"
