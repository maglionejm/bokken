"""Interview channels: how a question reaches a real human and the answer returns.

The Channel port keeps the interviewer engine transport-agnostic. Terminal
ships in core with zero dependencies; richer transports (Twilio) live behind
optional extras and the same three methods.

Consent is a channel concern only in the narrow sense of *asking and reporting
what came back*: `open` returns a :class:`Consent` verdict and never decides
whether the interview may proceed, and never touches the journal. Consent is
affirmative or it does not exist - silence, a timeout, and an ambiguous reply
are all refusals, and the channel says which so the caller can surface the
difference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol

ConsentOutcome = Literal["granted", "declined", "no_response", "ambiguous"]


@dataclass(frozen=True)
class Consent:
    """What the participant actually said when asked to take part.

    `basis` is a plain sentence describing how consent was sought and what
    came back; it goes into the journal verbatim so the ledger never has to
    guess whether a human really opted in.
    """

    outcome: ConsentOutcome
    basis: str

    @property
    def granted(self) -> bool:
        return self.outcome == "granted"


class Channel(Protocol):
    label: str

    def open(self, participant: str) -> Consent: ...
    def send(self, text: str) -> None: ...
    def receive(self) -> str: ...  # blocks until the participant answers
    def close(self, farewell: str) -> None: ...


class ChannelUnavailable(RuntimeError):
    pass


class ConsentNotGranted(ChannelUnavailable):
    """The participant did not affirmatively opt in, so no interview happens."""

    def __init__(self, outcome: ConsentOutcome, message: str) -> None:
        super().__init__(message)
        self.outcome = outcome


AFFIRMATIVE = frozenset(
    {"OK", "OKAY", "SI", "SÍ", "S", "YES", "Y", "VALE", "ACEPTO", "EMPEZAR", "START"}
)
DECLINE = frozenset({"STOP", "NO", "N", "BAJA", "CANCEL", "CANCELAR", "UNSUBSCRIBE"})
_PUNCTUATION = ".,;:!?¡¿'\"()[]-"


def classify_reply(reply: str) -> ConsentOutcome:
    """Read a reply as an opt-in decision, erring towards not interviewing.

    Only a bare affirmative grants consent: a "no" anywhere in the reply
    declines, nothing at all is `no_response`, and everything else - including
    "who is this?" and "si, si tuviera tiempo" - is `ambiguous`. Every outcome
    but `granted` stops the interview, so the loose cases cost a lost interview,
    never an unwanted one.
    """
    words = [w for w in (t.strip(_PUNCTUATION).upper() for t in reply.split()) if w]
    if not words:
        return "no_response"
    if any(w in DECLINE for w in words):
        return "declined"
    if len(words) == 1 and words[0] in AFFIRMATIVE:
        return "granted"
    return "ambiguous"


class TerminalChannel:
    """The founder relays the interview live (in person, phone, or screen share)."""

    label = "terminal"
    CONSENT_SCRIPT = (
        "Read this to the participant before starting: taking part is voluntary, "
        "their answers are used only for product research, and they can stop at "
        "any time."
    )
    CONSENT_BASIS: ClassVar[dict[str, str]] = {
        "granted": (
            "the operator attested, live at the terminal, that the participant "
            "consented in their own words"
        ),
        "declined": "the operator reported that the participant declined",
        "ambiguous": "the operator's answer was not an affirmative confirmation of consent",
        "no_response": "the operator did not confirm consent at the terminal",
    }

    def open(self, participant: str) -> Consent:
        print(f"--- validation interview with {participant} (Ctrl-C to stop) ---")
        print(self.CONSENT_SCRIPT)
        try:
            answer = input("Did the participant consent, in their own words? (yes/no): ")
        except EOFError:  # no operator present is no confirmation
            answer = ""
        outcome = classify_reply(answer)
        return Consent(outcome, self.CONSENT_BASIS[outcome])

    def send(self, text: str) -> None:
        print(f"\nINTERVIEWER: {text}")

    def receive(self) -> str:
        return input(f"{'PARTICIPANT'}: ").strip()

    def close(self, farewell: str) -> None:
        print(f"\nINTERVIEWER: {farewell}\n--- interview ended ---")


class TwilioChannel:
    """SMS/WhatsApp over Twilio's Messages API - polling, no webhook server.

    Requires the optional `interview` extra and TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN, TWILIO_FROM in the environment. The raw phone number
    never reaches the journal - callers pass a participant label.

    The consent request is sent exactly once and answered exactly once: no
    reminder, no retry, no second attempt to talk someone into it.
    """

    label = "twilio"
    POLL_SECONDS = 10
    ANSWER_TIMEOUT_SECONDS = 15 * 60
    CONSENT = (
        "Hola! Soy el asistente de investigacion de un equipo de producto. "
        "Te haremos unas preguntas breves; tus respuestas se usan solo para "
        "investigacion. Responde OK para empezar, o STOP para no participar."
    )
    CONSENT_BASIS: ClassVar[dict[str, str]] = {
        "granted": "the participant replied to the consent message with a bare affirmative",
        "declined": "the participant replied to the consent message declining",
        "ambiguous": "the reply to the consent message was not an affirmative opt-in",
        "no_response": "no reply to the consent message within the answer window",
    }

    def __init__(self, to_number: str) -> None:
        import os

        try:
            from twilio.rest import Client
        except ImportError as exc:  # pragma: no cover - import guard
            raise ChannelUnavailable("twilio is not installed (uv sync --extra interview)") from exc
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.from_number = os.environ.get("TWILIO_FROM", "")
        if not (sid and token and self.from_number):
            raise ChannelUnavailable(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM must be set"
            )
        self.client = Client(sid, token)
        self.to_number = to_number
        self._last_poll = None

    def _send(self, body: str) -> None:
        self.client.messages.create(to=self.to_number, from_=self.from_number, body=body)

    def open(self, participant: str) -> Consent:
        from datetime import UTC, datetime

        self._last_poll = datetime.now(UTC)
        self._send(self.CONSENT)
        outcome = classify_reply(self.receive())
        basis = self.CONSENT_BASIS[outcome]
        if outcome == "no_response":
            basis = f"{basis} of {self.ANSWER_TIMEOUT_SECONDS // 60} minutes"
        return Consent(outcome, basis)

    def send(self, text: str) -> None:
        self._send(text)

    def receive(self) -> str:
        import time
        from datetime import UTC

        deadline = time.monotonic() + self.ANSWER_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            inbound = self.client.messages.list(from_=self.to_number, to=self.from_number, limit=5)
            fresh = [
                m
                for m in inbound
                if m.date_sent and m.date_sent.replace(tzinfo=UTC) > self._last_poll
            ]
            if fresh:
                newest = max(fresh, key=lambda m: m.date_sent)
                self._last_poll = newest.date_sent.replace(tzinfo=UTC)
                return (newest.body or "").strip()
            time.sleep(self.POLL_SECONDS)
        return ""  # timeout -> engine closes gracefully

    def close(self, farewell: str) -> None:
        self._send(farewell)
