"""Pre-flight cost estimate: predict a run's tokens + list-price cost by derivation.

No session, no `ModelRouter`, no provider SDK, no network, no journal. The number
is a *modeled estimate* built from three definitions the post-run surfaces already
trust, so a prediction and its later ``bokken costs`` receipt speak one language:

- the per-routing-class token profile ``demo.provider.USAGE_BY_CLASS``;
- the single pricing function ``report.context.call_cost_usd``, priced on the
  **served** model the brief's provider/model routing resolves to (via the same
  ``resolve_routing`` / ``session_model_config`` a created session uses);
- the functional lane split ``report.context.functional_bucket``.

The estimate is honest about being an estimate: it is a low-high range (never a
single false-precision number), it states its assumptions, and it never claims to
be a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

from bokken.demo.provider import USAGE_BY_CLASS
from bokken.journal import RoutingClass
from bokken.models import resolve_routing, session_model_config
from bokken.report.context import call_cost_usd, functional_bucket


@dataclass(frozen=True)
class _PromptProfile:
    prompt_id: str
    routing_class: RoutingClass
    fixed_calls: int
    per_persona_calls: int


# An illustrative, deliberately lean single-pass DT run: which prompts execute and
# how many times, keyed to the routing class each stage invokes them on. Two call
# counts per entry: a fixed part (runs once per run) and a per-persona part (runs
# once per panel member). Research-lane per-persona work - persona interview turns
# and per-persona outcome scoring - is what makes a larger panel cost more. The
# prompt ids and routing classes mirror the stage engines; this table is a modeled
# profile of a typical run, not a measurement of any particular brief. Ordering
# follows the DT loop (explore -> empathize -> define -> ideate -> prototype ->
# test), so the breakdown reads top to bottom.
PROMPT_PROFILE: tuple[_PromptProfile, ...] = (
    _PromptProfile("explore/capability_map", "cognition", 1, 0),
    _PromptProfile("empathize/interview_program", "research", 1, 0),
    # One grounded interview turn per persona, plus one sidekick corpus read to
    # scope each persona's answer: the panel-size-sensitive core of the estimate.
    _PromptProfile("sidekick/context_query", "sidekick", 0, 1),
    _PromptProfile("empathize/persona_turn", "research", 0, 1),
    _PromptProfile("empathize/outcomes", "research", 1, 0),
    _PromptProfile("empathize/outcome_scores", "research", 0, 1),
    _PromptProfile("define/cluster", "cognition", 1, 0),
    _PromptProfile("define/candidates", "cognition", 1, 0),
    _PromptProfile("define/select", "cognition", 1, 0),
    _PromptProfile("ideate/diverge", "cognition", 3, 0),
    _PromptProfile("ideate/novelty", "extraction", 3, 0),
    _PromptProfile("ideate/skeptic_challenge", "challenge", 1, 0),
    _PromptProfile("ideate/converge", "challenge", 3, 0),
    _PromptProfile("prototype/assumptions", "cognition", 1, 0),
    _PromptProfile("prototype/fidelity", "cognition", 1, 0),
    _PromptProfile("prototype/artifact", "generation", 2, 0),
    # Test re-uses the panel: one evaluation per persona, then one recommendation.
    _PromptProfile("test/evaluate", "challenge", 0, 1),
    _PromptProfile("test/recommend", "challenge", 1, 0),
    _PromptProfile("handoff/specify", "generation", 1, 0),
)

# The spread band: the modeled point estimate is the centre of a +/- range so the
# figure reads as an estimate with variance, not a single precise number. A run's
# real usage varies with loop-backs, abstentions, and per-call token counts, none
# of which a pre-flight derivation can know.
SPREAD = 0.30

CAVEAT = (
    "This is a modeled estimate from an illustrative token profile, not a "
    "measurement of this brief and not a guaranteed cost. Once a run exists, "
    "`bokken costs` reports the actual list price from the journaled calls."
)

_LANES: tuple[str, ...] = ("exploration", "research", "synthesis")


@dataclass(frozen=True)
class LaneEstimate:
    """One functional lane's modeled calls, tokens, and cost."""

    lane: str  # exploration | research | synthesis
    calls: int
    tokens: int
    cost_usd: float


@dataclass(frozen=True)
class Estimate:
    """The derivation result: a range, a per-lane breakdown, and the assumptions."""

    panel_size: int
    provider: str
    model: str | None
    cost_point_usd: float
    cost_low_usd: float
    cost_high_usd: float
    total_calls: int
    total_tokens: int
    lanes: tuple[LaneEstimate, ...]
    assumptions: tuple[str, ...]
    caveat: str


def _class_tokens(routing_class: RoutingClass) -> int:
    """All billed tokens the profile ascribes to one call on this class."""
    usage = USAGE_BY_CLASS.get(routing_class, {})
    return sum(int(v or 0) for v in usage.values())


def estimate_run(
    panel_size: int,
    *,
    provider: str = "anthropic",
    model: str | None = None,
) -> Estimate:
    """Derive a modeled cost + token estimate for a run of the given shape.

    ``session_model_config`` validates the provider/model exactly as
    ``bokken new`` would (so an impossible combination is refused here, before
    any estimate is produced), and ``resolve_routing`` maps each routing class
    to the model that would actually serve it - the same served model
    ``bokken costs`` prices later.
    """
    if panel_size < 1:
        raise ValueError("panel size must be at least 1")
    # Validate + build the routing override exactly as a created session would,
    # then resolve to the served model per routing class.
    config = session_model_config(provider, model)
    routing = resolve_routing(config.get("routing"), provider)

    lane_calls: dict[str, int] = dict.fromkeys(_LANES, 0)
    lane_tokens: dict[str, int] = dict.fromkeys(_LANES, 0)
    lane_cost: dict[str, float] = dict.fromkeys(_LANES, 0.0)

    for entry in PROMPT_PROFILE:
        calls = entry.fixed_calls + entry.per_persona_calls * panel_size
        if calls == 0:
            continue
        lane = functional_bucket(entry.prompt_id)
        served_model = routing[entry.routing_class]
        usage = USAGE_BY_CLASS.get(entry.routing_class, {})
        per_call_cost = call_cost_usd(served_model, usage)
        lane_calls[lane] += calls
        lane_tokens[lane] += calls * _class_tokens(entry.routing_class)
        lane_cost[lane] += calls * per_call_cost

    lanes = tuple(
        LaneEstimate(
            lane=lane,
            calls=lane_calls[lane],
            tokens=lane_tokens[lane],
            cost_usd=round(lane_cost[lane], 4),
        )
        # Fixed order: the same exploration/research/synthesis vocabulary the
        # costs functional rollup uses.
        for lane in _LANES
    )
    # The point estimate is the sum of the (rounded) lane costs, so the three
    # lanes always reconcile to the headline figure exactly.
    point = round(sum(lane.cost_usd for lane in lanes), 4)
    assumptions = (
        f"Panel size assumed: {panel_size} personas "
        "(more personas add per-persona research-lane calls).",
        "Token profile: the illustrative per-routing-class table "
        "(demo provider `USAGE_BY_CLASS`), a modeled profile - not a measurement "
        "of this brief.",
        "Scope: one forward pass of the Design Thinking loop; real runs may "
        "loop back, abstain, or vary per-call token counts.",
        f"Priced on the served model per routing class via provider "
        f"'{provider}'" + (f" with model override '{model}'." if model else "."),
    )
    return Estimate(
        panel_size=panel_size,
        provider=provider,
        model=model,
        cost_point_usd=point,
        cost_low_usd=round(point * (1 - SPREAD), 4),
        cost_high_usd=round(point * (1 + SPREAD), 4),
        total_calls=sum(lane.calls for lane in lanes),
        total_tokens=sum(lane.tokens for lane in lanes),
        lanes=lanes,
        assumptions=assumptions,
        caveat=CAVEAT,
    )
