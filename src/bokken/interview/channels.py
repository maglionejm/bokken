"""Interview channels: how a question reaches a real human and the answer returns.

The Channel port keeps the interviewer engine transport-agnostic. Terminal
ships in core with zero dependencies; richer transports (Twilio) live behind
optional extras and the same three methods.
"""

from __future__ import annotations

from typing import Protocol


class Channel(Protocol):
    def open(self, participant: str) -> None: ...
    def send(self, text: str) -> None: ...
    def receive(self) -> str: ...  # blocks until the participant answers
    def close(self, farewell: str) -> None: ...


class ChannelUnavailable(RuntimeError):
    pass


class TerminalChannel:
    """The founder relays the interview live (in person, phone, or screen share)."""

    def open(self, participant: str) -> None:
        print(f"--- validation interview with {participant} (Ctrl-C to stop) ---")

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
    """

    POLL_SECONDS = 10
    ANSWER_TIMEOUT_SECONDS = 15 * 60
    CONSENT = (
        "Hola! Soy el asistente de investigacion de un equipo de producto. "
        "Te haremos unas preguntas breves; tus respuestas se usan solo para "
        "investigacion. Responde OK para empezar, o STOP para no participar."
    )

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

    def open(self, participant: str) -> None:
        from datetime import UTC, datetime

        self._last_poll = datetime.now(UTC)
        self._send(self.CONSENT)
        first = self.receive()
        if first.strip().upper() in ("STOP", "NO", "BAJA"):
            raise ChannelUnavailable("participant declined consent")

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
