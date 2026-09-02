"""Runner construction for the CLI. Tests monkeypatch ``router_factory``."""

from __future__ import annotations

from pathlib import Path

from bokken.journal import replay
from bokken.journal.store import read_events
from bokken.kata import MVP_MOVES, Kata
from bokken.orchestrator import InputPort, NoInputPort, Runner
from bokken.stages import RouterFactory, engine_suite


def router_factory() -> RouterFactory:
    from bokken.stages import provider_router_factory

    return provider_router_factory()


class TerminalInputPort:
    """Interactive port: plain prompts that always show the session's stage."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir

    def ask(self, question: str, *, kind: str = "text") -> str:
        import typer

        stage = replay(read_events(self.session_dir)).stage
        return typer.prompt(f"[{stage}] {question}", default="", show_default=False)


def build_runner(session_dir: Path, *, interactive: bool = True) -> Runner:
    port: InputPort = TerminalInputPort(session_dir) if interactive else NoInputPort()
    return Runner(
        session_dir,
        engines=engine_suite(router_factory()),
        input_port=port,
        kata_factory=lambda store: Kata(MVP_MOVES, store),
    )
