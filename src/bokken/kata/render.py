"""Move output rendering under the tone contract.

Neutral, warm, brief. Critiques are depersonalized: they address claims and
options, never persons. Deliberate counter-positions are explicitly labeled.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bokken.kata.registry import TriggerFire

DEVILS_ADVOCATE_LABEL = "[deliberate counter-position]"

_TEMPLATES: dict[str, str] = {
    "stage_contract": (
        "Opening {stage}. Goal: {goal}. Method: {method}. We move on when: {exit_bar}."
    ),
    "hmw_reframe": (
        "The current problem statement embeds a solution: {statement!r}. "
        "Reframing as a question: How might we {reframe}?"
    ),
    "assumption_flag": (
        "Logging as unvalidated: the claim {claim!r} is not yet supported by "
        "evidence in this session. It goes on the assumption register."
    ),
    "timebox_pivot": (
        "Idea novelty has decayed ({novelty_rate:.0%} new against a floor of "
        "{floor:.0%}). Proposing we move from divergence to convergence."
    ),
    "synthesis_readback": ("Here is what I heard so far: {synthesis} Correct me where I am wrong."),
    "devils_advocate": (
        DEVILS_ADVOCATE_LABEL + " Consensus formed quickly with no reservations "
        "on record. A case for the other side: {counter}"
    ),
    "parking_lot": (
        "Parking the thread {topic!r} - it is outside the current problem "
        "statement. It stays on record and can be picked up later."
    ),
    "loopback_proposal": (
        "A test result contradicts earlier work: {contradiction}. "
        "Proposing we return to {target_stage} rather than proceed on a "
        "weakened foundation."
    ),
    "close_and_commit": ("Closing the session. Binding commitments: {commitments}"),
}


def render_move(move_id: str, fire: TriggerFire, mode: str) -> str:
    """Render a move's user/panel-facing text. Founder mode phrases moves as
    prompts to the human; dojo mode as autonomous facilitation injections —
    the substance is identical."""
    template = _TEMPLATES[move_id]
    text = template.format(**fire.params)
    if mode == "founder" and move_id in ("timebox_pivot", "loopback_proposal"):
        text += " Say 'go ahead' to accept or tell me what to do instead."
    return text
