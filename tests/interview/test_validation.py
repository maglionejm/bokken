"""Validation interviews: guide, honest labels, bounded loop, rescoring."""

from pathlib import Path

import pytest

from bokken.interview import build_guide, run_validation_interview
from bokken.interview.channels import Consent, ConsentNotGranted, TerminalChannel
from bokken.interview.engine import REFUSAL
from bokken.interview.guide import Guide, journal_guide
from bokken.journal import Actor, read_events
from bokken.journal.store import JournalStore
from bokken.models import ModelRouter
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs, make_runner

GRANTED = Consent("granted", "test double: affirmative reply to the consent request")


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


class FakeChannel:
    label = "fake"

    def __init__(self, consent: Consent = GRANTED):
        self.sent = []
        self.consent = consent
        self.opens = 0

    def open(self, participant):
        self.participant = participant
        self.opens += 1
        return self.consent

    def send(self, text):
        self.sent.append(text)

    def receive(self):
        return "Si, el mes pasado me paso exactamente eso con la factura."

    def close(self, farewell):
        self.farewell = farewell


@pytest.fixture
def bare_store(tmp_path: Path):
    """A journal with nothing but a session, for consent-boundary tests."""
    session_dir = tmp_path / "sessions" / "consent"
    session_dir.mkdir(parents=True)
    with JournalStore.open(session_dir) as store:
        store.append(
            type="session.created",
            stage="intake",
            actor=Actor(kind="system", name="orchestrator"),
            payload={"name": "consent", "mode": "founder", "brief": BRIEF, "config": {}},
        )
        yield store


def test_guide_interview_and_rescoring(tmp_path):
    from bokken.orchestrator import create_session

    session_dir = create_session(
        "validate-e2e",
        brief={**BRIEF, "inputs": make_inputs(tmp_path)},
        mode="dojo",
        gate_policy="none",
        config_extra={"panel": {"size": 6, "seed": 11}},
    )
    provider = ScriptedProvider()
    assert make_runner(session_dir, provider).run().halt == "completed"

    with JournalStore.open(session_dir) as store:
        from bokken.journal import Actor

        store.append(
            type="assumption.registered",
            stage=None,
            actor=Actor(kind="agent", name="facilitator"),
            payload={
                "statement": "commuters would actually press a confirmation button",
                "impact": "high",
                "uncertainty": "high",
            },
        )
        guide = build_guide(store)
        assert not guide.empty
        journal_guide(store, guide)
        channel = FakeChannel()
        router = ModelRouter(store, provider)
        exchanges = run_validation_interview(
            store, router, guide, channel, participant="Ana (piloto real)"
        )
    assert exchanges == 1 and channel.sent
    events = list(read_events(session_dir))
    kinds = [e.payload.get("kind") for e in events if e.type == "artifact.generated"]
    assert "validation_guide" in kinds
    real = [
        e
        for e in events
        if e.type == "evidence.captured"
        and str(e.payload.get("source", "")).startswith("validation interview")
    ]
    assert real and all(e.actor.kind == "human" for e in real)
    assert all(e.payload["confidence_class"] == "reported" for e in real)
    # the contact and its outcome are on record before the first question went out
    requested = [e for e in events if e.type == "interview.consent_requested"]
    resolved = [e for e in events if e.type == "interview.consent_resolved"]
    assert len(requested) == 1 and len(resolved) == 1
    assert resolved[0].payload["outcome"] == "granted"
    assert resolved[0].payload["participant"] == "Ana (piloto real)"
    assert resolved[0].payload["basis"] == GRANTED.basis
    assert requested[0].seq < resolved[0].seq < real[0].seq
    rescored = [
        e
        for e in events
        if e.type == "assumption.scored" and e.actor.name == "validation-interviewer"
    ]
    assert rescored and real[0].id in rescored[0].refs


class FailingRouter:
    """Every interviewer turn fails: the model is down mid-interview."""

    def invoke(self, *args, **kwargs):
        from bokken.models.router import ModelOutcome

        return ModelOutcome(status="error", detail="provider capacity")


def test_mid_interview_failure_closes_the_channel_and_journals_debt(bare_store):
    channel = FakeChannel()
    guide = Guide(debt_questions=["Que hiciste la ultima vez que fallo el pago?"])
    exchanges = run_validation_interview(
        bare_store, FailingRouter(), guide, channel, participant="Ana (piloto real)"
    )
    assert exchanges == 0
    assert channel.farewell  # the consented human was not left hanging
    assert not channel.sent  # no question ever went out
    abstained = [e for e in bare_store.events() if e.type == "evidence.abstained"]
    assert len(abstained) == 1
    assert abstained[0].payload["question"] == guide.debt_questions[0]
    assert "aborted mid-run" in abstained[0].payload["gap"]
    assert "error" in abstained[0].payload["gap"]


class BlankQuestionRouter:
    """The interviewer keeps choosing ask, but produces no question text."""

    def invoke(self, *args, **kwargs):
        from bokken.models.router import ModelOutcome
        from bokken.stages.schemas import InterviewerTurn

        return ModelOutcome(
            status="ok",
            data=InterviewerTurn(action="ask", question="   "),
            model="claude-fable-5",
        )


def test_blank_question_aborts_instead_of_sending_nothing(bare_store):
    """An empty send would crash Twilio with nothing on the record: a blank
    ask/followup takes the same abort path as a failed interviewer call."""
    channel = FakeChannel()
    guide = Guide(debt_questions=["Que hiciste la ultima vez que fallo el pago?"])
    exchanges = run_validation_interview(
        bare_store, BlankQuestionRouter(), guide, channel, participant="Ana (piloto real)"
    )
    assert exchanges == 0
    assert not channel.sent  # the blank question never reached the channel
    assert channel.farewell  # the consented human was not left hanging
    abstained = [e for e in bare_store.events() if e.type == "evidence.abstained"]
    assert len(abstained) == 1
    assert abstained[0].payload["question"] == guide.debt_questions[0]
    assert "blank ask question" in abstained[0].payload["gap"]
    assert abstained[0].actor.model == "claude-fable-5"  # the turn that produced it


def _fake_twilio(monkeypatch, inbound: list[str]) -> list[str]:
    """Install a fake twilio SDK. `inbound` is what the number replies, in order
    (empty = the number never replies). Returns the list of outbound bodies."""
    import sys
    import types
    from datetime import UTC, datetime, timedelta

    sent: list[str] = []
    queue = list(inbound)

    class FakeMessages:
        def __init__(self):
            self.now = datetime.now(UTC)

        def create(self, to, from_, body):
            sent.append(body)

        def list(self, from_, to, limit):
            if not queue:
                return []
            reply = types.SimpleNamespace(
                body=queue.pop(0), date_sent=self.now + timedelta(seconds=len(sent))
            )
            return [reply]

    fake_client = types.SimpleNamespace(messages=FakeMessages())
    twilio_mod = types.ModuleType("twilio")
    rest_mod = types.ModuleType("twilio.rest")
    rest_mod.Client = lambda sid, token: fake_client
    twilio_mod.rest = rest_mod
    monkeypatch.setitem(sys.modules, "twilio", twilio_mod)
    monkeypatch.setitem(sys.modules, "twilio.rest", rest_mod)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC-test")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWILIO_FROM", "+15550000000")
    return sent


def _twilio_channel(silent: bool = False):
    from bokken.interview.channels import TwilioChannel

    channel = TwilioChannel("+34600000000")
    channel.POLL_SECONDS = 0
    if silent:
        channel.ANSWER_TIMEOUT_SECONDS = 0  # do not wait 15 real minutes for silence
    return channel


def test_twilio_channel_consent_and_polling(monkeypatch):
    sent = _fake_twilio(monkeypatch, ["OK", "OK"])
    channel = _twilio_channel()
    consent = channel.open("Ana (real)")
    assert consent.granted and consent.outcome == "granted"
    assert sent[0].startswith("Hola!")  # consent goes first
    channel.send("Cuentame de tu ultima factura.")
    answer = channel.receive()
    assert answer == "OK"
    channel.close("Gracias!")
    assert len(sent) == 3


@pytest.mark.parametrize(
    ("inbound", "outcome"),
    [
        ([], "no_response"),  # the number never replies: silence is not consent
        (["quien es?"], "ambiguous"),  # a question back is not consent either
        (["Si, si tuviera tiempo"], "ambiguous"),  # a hedge is not a bare opt-in
        (["STOP"], "declined"),
        (["No, gracias"], "declined"),  # a "no" anywhere is a decline
    ],
)
def test_twilio_consent_is_affirmative_or_nothing(monkeypatch, inbound, outcome):
    sent = _fake_twilio(monkeypatch, inbound)
    channel = _twilio_channel(silent=not inbound)
    consent = channel.open("Ana (real)")
    assert consent.outcome == outcome and not consent.granted
    assert consent.basis  # the ledger always gets a reason in words
    assert len(sent) == 1  # only the consent request; no question, no reminder


def test_twilio_receive_joins_all_fresh_messages_oldest_first(monkeypatch):
    import types
    from datetime import UTC, datetime, timedelta

    _fake_twilio(monkeypatch, [])
    channel = _twilio_channel()
    now = datetime.now(UTC)
    channel._last_poll = now - timedelta(minutes=5)
    older = types.SimpleNamespace(body="primera parte", date_sent=now - timedelta(seconds=60))
    newer = types.SimpleNamespace(body="segunda parte", date_sent=now - timedelta(seconds=30))
    channel.client = types.SimpleNamespace(
        # Twilio lists newest first; the reply must still read oldest first.
        messages=types.SimpleNamespace(list=lambda from_, to, limit: [newer, older])
    )
    assert channel.receive() == "primera parte\nsegunda parte"
    assert channel._last_poll == newer.date_sent


@pytest.mark.parametrize(
    ("answer", "outcome"),
    [
        ("yes", "granted"),
        ("si", "granted"),
        ("no", "declined"),
        ("", "no_response"),
        ("she is thinking about it", "ambiguous"),
    ],
)
def test_terminal_channel_requires_an_operator_confirmation(monkeypatch, answer, outcome):
    monkeypatch.setattr("builtins.input", lambda prompt="": answer)
    consent = TerminalChannel().open("Ana (real)")
    assert consent.outcome == outcome
    assert consent.granted is (outcome == "granted")


def test_terminal_channel_without_a_terminal_is_not_consent(monkeypatch):
    def no_stdin(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_stdin)
    assert TerminalChannel().open("Ana (real)").outcome == "no_response"


@pytest.mark.parametrize("outcome", ["no_response", "ambiguous", "declined"])
def test_interview_never_starts_without_affirmative_consent(bare_store, outcome):
    channel = FakeChannel(Consent(outcome, f"test double: {outcome}"))
    guide = Guide(debt_questions=["Que hiciste la ultima vez que fallo el pago?"])
    # router=None: a refused contact must not reach the model at all.
    with pytest.raises(ConsentNotGranted) as caught:
        run_validation_interview(bare_store, None, guide, channel, participant="Ana (piloto real)")

    assert caught.value.outcome == outcome
    assert str(caught.value) == REFUSAL[outcome]
    assert not channel.sent  # no interview question ever reached the participant
    assert channel.opens == 1  # asked exactly once: no retry loop pestering the number

    events = list(bare_store.events())
    requested = [e for e in events if e.type == "interview.consent_requested"]
    resolved = [e for e in events if e.type == "interview.consent_resolved"]
    assert len(requested) == 1 and len(resolved) == 1
    assert requested[0].payload["participant"] == "Ana (piloto real)"
    assert requested[0].payload["channel"] == "fake"
    assert resolved[0].payload["outcome"] == outcome
    assert resolved[0].payload["basis"] == f"test double: {outcome}"
    assert resolved[0].refs == [requested[0].id]  # the outcome links to the contact
    assert requested[0].actor.kind == "agent"  # the run owns the contact, not the human
    # a refused contact is never laundered into evidence
    assert not [e for e in events if e.type.startswith("evidence.")]


def test_refusal_reasons_distinguish_a_decline_from_silence():
    assert "declined" in REFUSAL["declined"]
    assert "no reply" in REFUSAL["no_response"]
    assert "not an affirmative opt-in" in REFUSAL["ambiguous"]
    assert len(set(REFUSAL.values())) == 3
