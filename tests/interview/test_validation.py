"""Validation interviews: guide, honest labels, bounded loop, rescoring."""

from pathlib import Path

import pytest

from bokken.interview import build_guide, run_validation_interview
from bokken.interview.guide import journal_guide
from bokken.journal import read_events
from bokken.journal.store import JournalStore
from bokken.models import ModelRouter
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs, make_runner


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    return tmp_path


class FakeChannel:
    def __init__(self):
        self.sent = []

    def open(self, participant):
        self.participant = participant

    def send(self, text):
        self.sent.append(text)

    def receive(self):
        return "Si, el mes pasado me paso exactamente eso con la factura."

    def close(self, farewell):
        self.farewell = farewell


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
    rescored = [
        e
        for e in events
        if e.type == "assumption.scored" and e.actor.name == "validation-interviewer"
    ]
    assert rescored and real[0].id in rescored[0].refs


def test_twilio_channel_consent_and_polling(monkeypatch):
    import sys
    import types
    from datetime import UTC, datetime, timedelta

    sent = []

    class FakeMessages:
        def __init__(self):
            self.now = datetime.now(UTC)

        def create(self, to, from_, body):
            sent.append(body)

        def list(self, from_, to, limit):
            reply = types.SimpleNamespace(
                body="OK", date_sent=self.now + timedelta(seconds=len(sent))
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

    from bokken.interview.channels import TwilioChannel

    channel = TwilioChannel("+34600000000")
    channel.POLL_SECONDS = 0
    channel.open("Ana (real)")
    assert sent[0].startswith("Hola!")  # consent goes first
    channel.send("Cuentame de tu ultima factura.")
    answer = channel.receive()
    assert answer == "OK"
    channel.close("Gracias!")
    assert len(sent) == 3
