"""The MCP surface: the same core, drivable by agents. Pure adapter, no logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from bokken import contract
from bokken.journal import (
    Actor,
    Brief,
    list_sessions,
    query,
    replay,
    resolve_session_dir,
)
from bokken.journal.schema import short_id
from bokken.journal.store import read_events
from bokken.orchestrator import InputRequired, Runner, create_session

mcp = MCPServer(
    "bokken",
    instructions=(
        "Bokken runs Design Thinking sessions as durable, journaled processes. "
        "Sessions are addressed by name. run_session advances to the next halt "
        "(gate, pending input, stop, or completion); loop with resolve_gate / "
        "submit_input between runs."
    ),
)


def surfaced(fn):
    """Convert domain refusals into ToolErrors whose message reaches the client
    (mcp 2.x masks arbitrary exceptions as 'Error executing tool ...')."""
    import functools

    from pydantic import ValidationError

    from bokken.journal import WorkspaceError
    from bokken.journal.store import SessionLockedError
    from bokken.orchestrator import IllegalTransitionError, OrchestratorError
    from bokken.panel import PanelConfigError

    refused = (
        WorkspaceError,
        OrchestratorError,
        IllegalTransitionError,
        SessionLockedError,
        PanelConfigError,
        ValidationError,
        ValueError,
        FileNotFoundError,
    )

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except refused as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def _client_actor(ctx: Context) -> Actor:
    """Actor attribution from the MCP handshake — never from tool arguments."""
    name, version = "mcp-client", None
    try:
        params = ctx.session.client_params
        info = getattr(params, "client_info", None) or getattr(params, "clientInfo", None)
        if info is not None:
            name = info.name or name
            version = info.version
    except AttributeError:
        pass
    identity = f"{name}@{version}" if version else name
    return Actor(kind="agent", name=identity)


# --- input mailbox (Founder-mode questions answered programmatically) ---------


def _question_id(question: str) -> str:
    return short_id(question)


class MailboxPort:
    """Input port backed by workspace files: pending question out, answers in.

    Session *state* stays journal-derived; these files are only an input
    mailbox between run_session halts and submit_input calls.
    """

    def __init__(self, session_dir: Path) -> None:
        self.pending_path = session_dir / "pending_question.json"
        self.answers_path = session_dir / "answers.json"

    def ask(self, question: str, *, kind: str = "text") -> str:
        qid = _question_id(question)
        answers: dict[str, str] = {}
        if self.answers_path.exists():
            answers = json.loads(self.answers_path.read_text())
        if qid in answers:
            answer = answers.pop(qid)
            self.answers_path.write_text(json.dumps(answers))
            self.pending_path.unlink(missing_ok=True)
            return answer
        self.pending_path.write_text(json.dumps({"question_id": qid, "question": question}))
        raise InputRequired(question)

    def pending(self) -> dict[str, str] | None:
        if self.pending_path.exists():
            return json.loads(self.pending_path.read_text())
        return None

    def store_answer(self, question_id: str, answer: str) -> None:
        pending = self.pending()
        if pending is None or pending["question_id"] != question_id:
            raise ValueError(
                f"no pending question with id {question_id!r}; "
                "run_session first and read its pending_question"
            )
        answers: dict[str, str] = {}
        if self.answers_path.exists():
            answers = json.loads(self.answers_path.read_text())
        answers[question_id] = answer
        self.answers_path.write_text(json.dumps(answers))


def _runner(name: str) -> tuple[Runner, MailboxPort]:
    from bokken.cli import wiring
    from bokken.kata import MVP_MOVES, Kata
    from bokken.stages import engine_suite

    session_dir = resolve_session_dir(name)
    port = MailboxPort(session_dir)
    runner = Runner(
        session_dir,
        engines=engine_suite(wiring.router_factory()),
        input_port=port,
        kata_factory=lambda store: Kata(MVP_MOVES, store),
    )
    return runner, port


def _run_outcome(result: Any, port: MailboxPort) -> dict:
    outcome = contract.RunOutcome(
        halt=result.halt,
        stage=result.stage,
        detail=result.detail,
        pending_question=result.pending_question,
    ).model_dump()
    pending = port.pending()
    if pending is not None and result.halt == "input_pending":
        outcome["pending_question_id"] = pending["question_id"]
    return outcome


# --- tools --------------------------------------------------------------------


@mcp.tool()
@surfaced
def create_session_tool(
    name: str,
    brief: dict,
    mode: Literal["founder", "dojo"] = "dojo",
    gate_policy: str | list[str] | None = None,
    total_token_budget: int | None = None,
    panel_size: int = 6,
    seed: int = 7,
) -> dict:
    """Create a Design Thinking session. The brief needs problem_space,
    target_segments, success_criteria, risk_tolerance, and may declare inputs
    (repo path, metrics/discussion/document files)."""
    budgets = {"total_tokens": total_token_budget} if total_token_budget else None
    session_dir = create_session(
        name,
        brief=Brief.model_validate(brief),
        mode=mode,
        gate_policy=gate_policy,  # type: ignore[arg-type]
        budgets=budgets,
        config_extra={"panel": {"size": panel_size, "seed": seed}},
    )
    return contract.status_for_dir(name, session_dir).model_dump()


@mcp.tool()
@surfaced
def run_session(name: str, ctx: Context) -> dict:
    """Advance the session to its next halt (gate, input, stop, or completion).
    Completed runs are finalized automatically: Dossier, then handoff specs."""
    runner, port = _runner(name)
    outcome = _run_outcome(runner.run(actor=_client_actor(ctx)), port)
    if outcome.get("halt") == "completed":
        from bokken.cli import wiring
        from bokken.handoff import finalize_session

        finalization = finalize_session(runner.session_dir, wiring.router_factory())
        outcome["finalization"] = finalization.summary()
    return outcome


@mcp.tool()
@surfaced
def step_session(name: str, ctx: Context) -> dict:
    """Advance the session by at most one stage."""
    runner, port = _runner(name)
    return _run_outcome(runner.step(actor=_client_actor(ctx)), port)


@mcp.tool()
@surfaced
def stop_session(name: str, ctx: Context, reason: str | None = None) -> dict:
    """Stop the run (journaled human-initiated stop); the session stays resumable."""
    runner, _ = _runner(name)
    runner.stop(actor=_client_actor(ctx), detail=reason)
    return contract.status_for_dir(name, runner.session_dir).model_dump()


@mcp.tool()
@surfaced
def get_status(name: str) -> dict:
    """Where the session is and what blocks progress."""
    return contract.status_for_dir(name, resolve_session_dir(name)).model_dump()


@mcp.tool()
@surfaced
def list_sessions_tool() -> dict:
    """List sessions in the workspace."""
    return contract.list_result(list_sessions()).model_dump()


@mcp.tool()
@surfaced
def resolve_gate(
    name: str,
    resolution: Literal["approve", "reject"],
    ctx: Context,
    reason: str | None = None,
) -> dict:
    """Approve or reject the pending gate (rejection requires a reason)."""
    if resolution == "reject" and not reason:
        raise ValueError("gate rejection requires a reason")
    runner, _ = _runner(name)
    runner.resolve_gate(resolution=resolution, actor=_client_actor(ctx), reason=reason)
    state = replay(read_events(runner.session_dir))
    return contract.GateResult(resolution=resolution, stage=state.stage).model_dump()


@mcp.tool()
@surfaced
def request_loopback(name: str, to_stage: str, reason: str, ctx: Context) -> dict:
    """Loop back to an earlier stage (test->define, test->empathize, define->empathize)."""
    runner, _ = _runner(name)
    runner.request_loopback(to_stage=to_stage, reason=reason, actor=_client_actor(ctx))  # type: ignore[arg-type]
    return contract.LoopbackResult(to_stage=to_stage, stage=to_stage).model_dump()


@mcp.tool()
@surfaced
def submit_input(name: str, question_id: str, answer: str) -> dict:
    """Answer the session's pending Founder-mode question, then run_session again."""
    _, port = _runner(name)
    port.store_answer(question_id, answer)
    return {"stored": True, "question_id": question_id}


@mcp.tool()
@surfaced
def query_journal(
    name: str,
    type: str | None = None,
    stage: str | None = None,
    actor: str | None = None,
    since_seq: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Read ledger events with the same filters and canonical form as the CLI."""
    session_dir = resolve_session_dir(name)
    return [
        event.model_dump(mode="json")
        for event in query(
            session_dir,
            type=type,
            stage=stage,  # type: ignore[arg-type]
            actor=actor,  # type: ignore[arg-type]
            since_seq=since_seq,
            limit=limit,
        )
    ]


@mcp.tool()
@surfaced
def generate_handoff(name: str) -> dict:
    """Generate OpenSpec MVP specifications for the validated concept, ready to be
    ingested by a coding harness (refused for killed concepts)."""
    from bokken.cli import wiring
    from bokken.handoff import HandoffRefusedError
    from bokken.handoff import generate_handoff as _generate

    try:
        generated = _generate(resolve_session_dir(name), wiring.router_factory())
    except HandoffRefusedError as refusal:
        raise ToolError(str(refusal)) from refusal
    return contract.HandoffResult(**generated).model_dump()


@mcp.tool()
@surfaced
def generate_dossier(name: str) -> dict:
    """Generate the Session Dossier and return the export paths."""
    from bokken.dossier import generate

    md_path, json_path, status = generate(resolve_session_dir(name))
    return contract.DossierResult(
        markdown_path=str(md_path), json_path=str(json_path), status=status
    ).model_dump()


@mcp.tool()
@surfaced
def export_report(name: str) -> dict:
    """Export the run report (PPTX deck + self-contained HTML) and return the paths."""
    from bokken.report.generate import ReportError, generate_report

    try:
        pptx_path, html_path = generate_report(resolve_session_dir(name))
    except ReportError as err:
        raise ToolError(str(err)) from err
    return contract.ExportResult(pptx_path=str(pptx_path), html_path=str(html_path)).model_dump()


@mcp.tool()
@surfaced
def cost_report(name: str) -> dict:
    """Cost report from the journaled model calls (list-price estimate, cache hit rate)."""
    from bokken.dossier.model import build_model
    from bokken.report.context import cost_rows

    rows = cost_rows(build_model(resolve_session_dir(name)))
    hit = sum(r["cache_read"] for r in rows)
    raw = sum(r["input"] for r in rows)
    return {
        "rows": rows,
        "total_usd": round(sum(r["cost_usd"] for r in rows), 2),
        "cache_hit_rate": round(hit / (hit + raw), 3) if hit + raw else 0.0,
    }


# --- resources ------------------------------------------------------------------


@mcp.resource("bokken://sessions")
def sessions_resource() -> str:
    return contract.list_result(list_sessions()).model_dump_json(indent=2)


@mcp.resource("bokken://sessions/{name}/status")
def status_resource(name: str) -> str:
    return contract.status_for_dir(name, resolve_session_dir(name)).model_dump_json(indent=2)


@mcp.resource("bokken://sessions/{name}/journal")
def journal_resource(name: str) -> str:
    session_dir = resolve_session_dir(name)
    return "\n".join(event.model_dump_json() for event in read_events(session_dir))


@mcp.resource("bokken://sessions/{name}/dossier")
def dossier_resource(name: str) -> str:
    path = resolve_session_dir(name) / "dossier" / "dossier.json"
    if not path.exists():
        raise FileNotFoundError(f"no dossier generated yet for '{name}'; call generate_dossier")
    return path.read_text(encoding="utf-8")


def serve() -> None:
    """Run the MCP server on stdio."""
    mcp.run()
