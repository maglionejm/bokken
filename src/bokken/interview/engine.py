"""Agentic interviewer: a bounded, honest turn loop with a real human.

The model (research class) moderates: it picks the next guide question,
ladders into concrete incidents when an answer deserves it, and concludes
inside the turn budget. Every exchange journals as reported evidence with
human provenance for the participant; rescoring then confronts the untested
assumptions with what real people actually said.
"""

from __future__ import annotations

from bokken.interview.channels import Channel
from bokken.interview.guide import Guide
from bokken.journal import Actor, replay
from bokken.stages.schemas import InterviewerTurn, Rescoring

MAX_TURNS = 14
INTERVIEWER = Actor(kind="agent", name="validation-interviewer", model="claude-fable-5")


def _participant_actor(participant: str) -> Actor:
    return Actor(kind="human", name=participant)


def run_validation_interview(
    store, router, guide: Guide, channel: Channel, *, participant: str
) -> int:
    """Conduct one interview; returns the number of exchanges journaled."""
    channel.open(participant)
    transcript: list[str] = []
    exchanges = 0
    guide_text = guide.markdown()
    for _turn in range(MAX_TURNS):
        turn = router.invoke(
            "research",
            "validate/next_turn",
            stage=None,
            params={
                "guide": guide_text,
                "participant": participant,
                "transcript": "\n".join(transcript) or "(interview not started)",
            },
            schema=InterviewerTurn,
        )
        if not turn.ok or turn.data is None:
            break
        decision: InterviewerTurn = turn.data
        if decision.action == "conclude":
            channel.close(decision.question or "Thank you - this was genuinely useful.")
            break
        channel.send(decision.question)
        answer = channel.receive()
        if not answer:
            channel.close("Thank you for your time.")
            break
        transcript.append(f"Q: {decision.question}\nA: {answer}")
        store.append(
            type="evidence.captured",
            stage=None,
            actor=_participant_actor(participant),
            payload={
                "content": answer,
                "source": f"validation interview ({decision.action})",
                "confidence_class": "reported",
                "question": decision.question,
                "participant": participant,
            },
        )
        exchanges += 1
    else:
        channel.close("We are at time - thank you, this was genuinely useful.")
    if exchanges:
        _rescore(store, router)
    return exchanges


def _rescore(store, router) -> None:
    """Confront untested assumptions with the real (reported, human) evidence."""
    state = replay(store.events())
    real = [
        (eid, item)
        for eid, item in state.evidence.items()
        if item.confidence_class == "reported" and item.source.startswith("validation interview")
    ]
    if not real:
        return
    untested = {
        aid: a for aid, a in state.assumptions.items() if (a.score or "untested") == "untested"
    }
    if not untested:
        return
    evidence_text = "\n".join(
        f"- {eid}: (from {item.speaker or 'participant'})" for eid, item in real
    )
    # content is not in replay state; feed the journal rows verbatim
    rows = []
    for event in store.events():
        if event.id in dict(real):
            rows.append(f"- {event.id}: {event.payload['content']}")
    assumptions_text = "\n".join(f"- {aid}: {a.statement}" for aid, a in untested.items())
    outcome = router.invoke(
        "challenge",
        "validate/rescore",
        stage=None,
        params={"assumptions": assumptions_text, "evidence": "\n".join(rows) or evidence_text},
        schema=Rescoring,
    )
    if not outcome.ok or outcome.data is None:
        return
    known_evidence = {eid for eid, _ in real}
    for scored in outcome.data.scores:
        if scored.assumption_id not in untested:
            continue
        refs = [r for r in scored.evidence_ids if r in known_evidence]
        if not refs:
            continue  # a rescoring without real evidence is not a rescoring
        store.append(
            type="assumption.scored",
            stage=None,
            actor=INTERVIEWER,
            payload={"score": scored.score, "rationale": scored.rationale},
            refs=[scored.assumption_id, *refs],
        )
