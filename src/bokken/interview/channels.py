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
