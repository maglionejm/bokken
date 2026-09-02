"""The bokken CLI: barista-style lifecycle verbs over durable, resumable sessions."""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel, ValidationError
from rich.console import Console

import bokken
from bokken import contract
from bokken.cli import wiring
from bokken.journal import (
    Actor,
    Brief,
    WorkspaceError,
    list_sessions,
    query,
    replay,
    resolve_session_dir,
    sessions_dir,
)
from bokken.journal.store import SessionLockedError, read_events
from bokken.models import RoutingConfigError, session_model_config
from bokken.orchestrator import (
    IllegalTransitionError,
    NoPendingGateError,
    OrchestratorError,
    RunResult,
    create_session,
)
from bokken.panel import PanelConfigError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Bokken: an agentic harness for Design Thinking. Sessions are durable and "
    "resumable by name; state lives in an append-only journal. "
    "Created by Juan Martin Maglione and Marc Puig.",
)
out = Console()

HUMAN = Actor(kind="human", name="operator")

_REFUSED = (
    WorkspaceError,
    OrchestratorError,
    IllegalTransitionError,
    NoPendingGateError,
    SessionLockedError,
    PanelConfigError,
    RoutingConfigError,
    ValidationError,
)


def _fail(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise typer.Exit(code)


def guarded(fn: Callable[..., Any]) -> Callable[..., Any]:
    import functools

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            print("interrupted; the session is resumable with `bokken run`", file=sys.stderr)
            raise typer.Exit(0) from None
        except _REFUSED as exc:
            _fail(str(exc), 2)
        except Exception as exc:  # unexpected
            import os

            if os.environ.get("BOKKEN_DEBUG"):
                raise
            _fail(f"unexpected error: {exc}", 1)

    return wrapper


def emit(result: BaseModel, as_json: bool, human: Callable[[], None]) -> None:
    if as_json:
        print(result.model_dump_json(indent=2))
    else:
        human()


def _run_result(result: RunResult) -> contract.RunOutcome:
    return contract.RunOutcome(
        halt=result.halt,
        stage=result.stage,
        detail=result.detail,
        pending_question=result.pending_question,
    )


def _print_run(result: contract.RunOutcome) -> None:
    line = f"halt: {result.halt} (stage: {result.stage})"
    if result.detail:
        line += f" - {result.detail}"
    out.print(line)
    if result.pending_question:
        out.print(f"pending question: {result.pending_question}")
    if result.finalization:
        out.print(f"finalization: {result.finalization}")


JsonFlag = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON on stdout.")]


@app.callback()
def _root() -> None:
    pass


@app.command("version")
def version() -> None:
    """Print the bokken version."""
    print(bokken.__version__)


@app.command("init")
@guarded
def init(
    template: Annotated[
        str | None,
        typer.Option(help="saas-retention, consumer-app, or internal-tool (skips prompts)."),
    ] = None,
    out_path: Annotated[
        Path, typer.Option("--out", help="Where to write the brief JSON.")
    ] = Path("bokken-brief.json"),
    as_json: JsonFlag = False,
) -> None:
    """Write a validated brief file from a template; prints the commands that use it."""
    from bokken.cli.templates import TEMPLATES, build_brief

    if template is not None:
        if template not in TEMPLATES:
            raise typer.BadParameter(f"unknown template; pick one of {sorted(TEMPLATES)}")
        brief_data = build_brief(template)
    else:
        names = sorted(TEMPLATES)
        out.print("Templates: " + ", ".join(f"{i + 1}) {n}" for i, n in enumerate(names)))
        pick = typer.prompt("Template", default="1")
        chosen = names[int(pick) - 1] if pick.strip().isdigit() else pick.strip()
        if chosen not in TEMPLATES:
            raise typer.BadParameter(f"unknown template; pick one of {names}")
        product = typer.prompt("Product name")
        brief_data = build_brief(chosen, product)
        brief_data["problem_space"] = typer.prompt(
            "Problem space", default=brief_data["problem_space"]
        )
        segments = typer.prompt(
            "Target segments (comma-separated)",
            default=", ".join(brief_data["target_segments"]),
        )
        brief_data["target_segments"] = [s.strip() for s in segments.split(",") if s.strip()]
        criteria = typer.prompt(
            "Success criteria (comma-separated)",
            default=", ".join(brief_data["success_criteria"]),
        )
        brief_data["success_criteria"] = [s.strip() for s in criteria.split(",") if s.strip()]
        repo = typer.prompt("Path to the product's repo (empty to skip)", default="")
        if repo.strip():
            brief_data["inputs"]["repo"] = str(Path(repo.strip()).expanduser().resolve())

    Brief.model_validate(brief_data)  # fail before touching disk
    out_path.write_text(json.dumps(brief_data, indent=2, ensure_ascii=False) + "\n")
    session = out_path.stem.removesuffix("-brief") or "my-product"
    if as_json:
        print(json.dumps({"brief": str(out_path), "template": template or "interactive"}))
        return
    out.print(f"brief written to {out_path}")
    out.print("next:")
    out.print(f"  bokken new {session} --brief {out_path}")
    out.print(f"  bokken run {session}")


@app.command("new")
@guarded
def new(
    name: str,
    brief: Annotated[
        Path | None, typer.Option(help="Brief as a JSON file (non-interactive).")
    ] = None,
    mode: Annotated[str, typer.Option(help="founder or dojo")] = "founder",
    provider: Annotated[str, typer.Option(help="anthropic or openai")] = "anthropic",
    model: Annotated[
        str | None, typer.Option(help="Use this model for frontier routing classes.")
    ] = None,
    reasoning_effort: Annotated[
        str | None, typer.Option(help="Reasoning effort: low, medium, or high.")
    ] = None,
    gates: Annotated[
        str | None, typer.Option(help="none, stage_boundaries, or CSV of stages")
    ] = None,
    budget: Annotated[int | None, typer.Option(help="Total token budget for the run.")] = None,
    repo: Annotated[
        Path | None, typer.Option(help="App repository to explore (code input).")
    ] = None,
    app_url: Annotated[
        str | None, typer.Option(help="Running instance of the product to walk through.")
    ] = None,
    allow_web_research: Annotated[
        bool,
        typer.Option(
            "--allow-web-research", help="Authorize deep web research on the selected concept."
        ),
    ] = False,
    metrics: Annotated[
        list[Path] | None, typer.Option(help="Business/performance metrics file.")
    ] = None,
    discussion: Annotated[
        list[Path] | None, typer.Option(help="Interview/discussion transcript.")
    ] = None,
    doc: Annotated[list[Path] | None, typer.Option(help="Other document input.")] = None,
    panel_size: Annotated[int, typer.Option(help="Synthetic panel size (dojo).")] = 6,
    seed: Annotated[int, typer.Option(help="Panel casting seed.")] = 7,
    as_json: JsonFlag = False,
) -> None:
    """Create a session: validate the brief, journal it, enter intake."""
    if brief is not None:
        brief_data = json.loads(brief.read_text(encoding="utf-8"))
    else:
        out.print("Brief intake. Answer plainly; you can loop back later.")
        brief_data = {
            "problem_space": typer.prompt("Problem space"),
            "target_segments": [
                s.strip() for s in typer.prompt("Target segments (comma-separated)").split(",")
            ],
            "success_criteria": [
                s.strip() for s in typer.prompt("Success criteria (comma-separated)").split(",")
            ],
            "risk_tolerance": typer.prompt("Risk tolerance", default="medium"),
            "constraints": [],
        }
    inputs = brief_data.setdefault("inputs", {})
    if repo:
        inputs["repo"] = str(repo.resolve())
    if app_url:
        inputs["app_url"] = app_url
    if allow_web_research:
        brief_data["allow_web_research"] = True
    if metrics:
        inputs.setdefault("metrics", []).extend(str(p.resolve()) for p in metrics)
    if discussion:
        inputs.setdefault("discussions", []).extend(str(p.resolve()) for p in discussion)
    if doc:
        inputs.setdefault("documents", []).extend(str(p.resolve()) for p in doc)

    gate_policy: Any = None
    if gates is not None:
        gate_policy = (
            gates
            if gates in ("none", "stage_boundaries")
            else [s.strip() for s in gates.split(",")]
        )
    # Default guardrail: a run stops honestly instead of surprising on cost.
    budgets = {"total_tokens": budget} if budget else {"total_tokens": 20_000_000}
    session_dir = create_session(
        name,
        brief=Brief.model_validate(brief_data),
        mode=mode,  # type: ignore[arg-type]
        gate_policy=gate_policy,
        budgets=budgets,
        config_extra={
            "panel": {"size": panel_size, "seed": seed},
            **session_model_config(provider, model, reasoning_effort),
        },
    )
    result = contract.status_for_dir(name, session_dir)
    emit(result, as_json, lambda: out.print(f"created session '{name}' at {session_dir}"))


@app.command("run")
@guarded
def run(name: str, as_json: JsonFlag = False) -> None:
    """Resume and continue the loop until a gate, input, stop, or completion.
    Completed runs are finalized automatically: Dossier, then handoff specs."""
    session_dir = resolve_session_dir(name)
    runner = wiring.build_runner(session_dir, interactive=not as_json)
    result = _run_result(runner.run(actor=HUMAN))
    if result.halt == "completed":
        from bokken.handoff import finalize_session

        finalization = finalize_session(session_dir, wiring.router_factory())
        result = result.model_copy(update={"finalization": finalization.summary()})
    emit(result, as_json, lambda: _print_run(result))


@app.command("step")
@guarded
def step(name: str, as_json: JsonFlag = False) -> None:
    """Advance the session by at most one stage."""
    session_dir = resolve_session_dir(name)
    runner = wiring.build_runner(session_dir, interactive=not as_json)
    result = _run_result(runner.step(actor=HUMAN))
    emit(result, as_json, lambda: _print_run(result))


@app.command("stop")
@guarded
def stop(name: str, reason: Annotated[str | None, typer.Option("--reason")] = None) -> None:
    """Stop the run (journaled as a human stop). The session stays resumable."""
    runner = wiring.build_runner(resolve_session_dir(name), interactive=False)
    runner.stop(actor=HUMAN, detail=reason)
    out.print(f"stopped '{name}' (resumable)")


@app.command("status")
@guarded
def status(name: str, as_json: JsonFlag = False) -> None:
    """Show where the session is and what blocks progress."""
    session_dir = resolve_session_dir(name)
    result = contract.status_for_dir(name, session_dir)

    def human() -> None:
        out.print(f"{result.name}: stage {result.stage} ({result.state}), mode {result.mode}")
        if result.pending_gate:
            g = result.pending_gate
            out.print(
                f"pending gate {g.gate_id} guards {g.from_stage} -> {g.to_stage}; "
                f"resolve with: {g.resolve_hint}"
            )
        if result.stopped_reason:
            out.print(f"stopped: {result.stopped_reason}")
        out.print(
            f"evidence {result.evidence_by_class}, research debt {result.research_debt}, "
            f"options alive {result.options_alive}, assumptions {result.assumptions_scored}, "
            f"tokens {result.tokens_spent}"
        )

    emit(result, as_json, human)


@app.command("list")
@guarded
def list_cmd(as_json: JsonFlag = False) -> None:
    """List sessions in the workspace."""
    result = contract.list_result(list_sessions())

    def human() -> None:
        if not result.sessions:
            out.print(f"no sessions in {sessions_dir()}")
        for s in result.sessions:
            out.print(f"{s.slug}: stage {s.stage}, mode {s.mode}, last event {s.last_ts}")

    emit(result, as_json, human)


@app.command("gate")
@guarded
def gate(
    name: str,
    resolution: Annotated[str, typer.Argument(help="approve or reject")],
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Resolve the pending gate."""
    if resolution not in ("approve", "reject"):
        _fail("resolution must be 'approve' or 'reject'", 2)
    if resolution == "reject" and not reason:
        _fail("rejection requires --reason", 2)
    runner = wiring.build_runner(resolve_session_dir(name), interactive=False)
    runner.resolve_gate(resolution=resolution, actor=HUMAN, reason=reason)  # type: ignore[arg-type]
    state = replay(read_events(runner.session_dir))
    result = contract.GateResult(resolution=resolution, stage=state.stage)
    emit(result, as_json, lambda: out.print(f"gate {resolution}d; stage {state.stage}"))


@app.command("back")
@guarded
def back(
    name: str,
    stage: str,
    reason: Annotated[str, typer.Option("--reason")],
    as_json: JsonFlag = False,
) -> None:
    """Loop back to an earlier stage (test->define, test->empathize, define->empathize)."""
    runner = wiring.build_runner(resolve_session_dir(name), interactive=False)
    runner.request_loopback(to_stage=stage, reason=reason, actor=HUMAN)  # type: ignore[arg-type]
    result = contract.LoopbackResult(to_stage=stage, stage=stage)
    emit(result, as_json, lambda: out.print(f"looped back to {stage}"))


@app.command("journal")
@guarded
def journal(
    name: str,
    type_filter: Annotated[str | None, typer.Option("--type", help="Event type or family.")] = None,
    stage: Annotated[str | None, typer.Option("--stage")] = None,
    actor: Annotated[str | None, typer.Option("--actor", help="human, agent, or system")] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Seq number or ISO timestamp; only later events."),
    ] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
    follow: Annotated[
        bool, typer.Option("--follow", help="Stream new events until Ctrl-C.")
    ] = False,
    as_json: JsonFlag = False,
) -> None:
    """Print ledger events (filters compose); --json emits canonical JSONL."""
    session_dir = resolve_session_dir(name)
    since_seq, since_ts = _parse_since(since)

    def render(event: Any) -> None:
        if as_json:
            print(event.model_dump_json())
        else:
            out.print(
                f"{event.seq:>5} {event.ts:%H:%M:%S} [{event.stage or '-'}] "
                f"{event.type} ({event.actor.kind}:{event.actor.name})"
            )

    if follow:
        from bokken.journal import follow as follow_events

        stop_event = threading.Event()
        try:
            for event in follow_events(session_dir, since_seq=since_seq or 0, stop=stop_event):
                if _matches(event, type_filter, stage, actor, since_ts):
                    render(event)
        except KeyboardInterrupt:
            return
    else:
        for event in query(
            session_dir,
            type=type_filter,
            stage=stage,  # type: ignore[arg-type]
            actor=actor,  # type: ignore[arg-type]
            since_seq=since_seq,
            since_ts=since_ts,
            limit=limit,
        ):
            render(event)


def _parse_since(since: str | None):
    """--since accepts a seq number or an ISO timestamp (naive = UTC)."""
    if since is None:
        return None, None
    if since.isdigit():
        return int(since), None
    from datetime import UTC, datetime

    try:
        ts = datetime.fromisoformat(since)
    except ValueError:
        _fail(f"--since must be a seq number or an ISO timestamp, got {since!r}", 2)
        raise  # unreachable; keeps type-checkers honest
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return None, ts


def _matches(
    event: Any,
    type_filter: str | None,
    stage: str | None,
    actor: str | None,
    since_ts: Any = None,
) -> bool:
    if since_ts is not None and event.ts < since_ts:
        return False
    from bokken.journal.query import _type_matches

    if type_filter is not None and not _type_matches(event.type, type_filter):
        return False
    if stage is not None and event.stage != stage:
        return False
    return not (actor is not None and event.actor.kind != actor)


@app.command("dossier")
@guarded
def dossier(name: str, as_json: JsonFlag = False) -> None:
    """Generate the Session Dossier (Parts A/B in markdown, Part C in JSON)."""
    from bokken.dossier import generate

    md_path, json_path, dossier_status = generate(resolve_session_dir(name))
    result = contract.DossierResult(
        markdown_path=str(md_path), json_path=str(json_path), status=dossier_status
    )
    emit(
        result,
        as_json,
        lambda: out.print(f"dossier ({dossier_status}):\n  {md_path}\n  {json_path}"),
    )


@app.command("demo")
@guarded
def demo(name: str = "demo", as_json: JsonFlag = False) -> None:
    """A complete run on the bundled Lanzadera case: no API key, no network, ~$0."""
    from bokken.demo import run_demo

    summary = run_demo(name)
    if as_json:
        print(json.dumps({k: str(v) for k, v in summary.items()}, indent=2))
        return
    out.print(f"halt: {summary['halt']} - {summary['finalization']}")
    out.print(f"report (html): {summary['report_html']}")
    out.print(f"report (deck): {summary['report_pptx']}")
    out.print(f"dossier:       {summary['dossier']}")
    out.print(
        "this demo cost $0.00 and made 0 network calls - a real run on your "
        f"product is typically $20-35 (`bokken costs {name}` for the math)"
    )


@app.command("validate")
@guarded
def validate(
    name: str,
    participant: Annotated[
        str, typer.Option(help="Participant label (never a phone number).")
    ] = "participant-1",
    channel: Annotated[str, typer.Option(help="terminal (more via extras)")] = "terminal",
    guide_only: Annotated[
        bool, typer.Option("--guide-only", help="Produce the guide and stop.")
    ] = False,
    to: Annotated[
        str | None, typer.Option(help="Phone for --channel twilio (E.164); never journaled.")
    ] = None,
) -> None:
    """Run a real validation interview against the session's research debt."""
    from bokken.interview import build_guide, run_validation_interview
    from bokken.interview.channels import TerminalChannel
    from bokken.interview.guide import journal_guide
    from bokken.journal.store import JournalStore

    session_dir = resolve_session_dir(name)
    with JournalStore.open(session_dir) as store:
        guide = build_guide(store)
        if guide.empty:
            _fail("nothing to validate: no research debt and no untested assumptions", 2)
        path = journal_guide(store, guide)
        out.print(f"guide: {session_dir / path}")
        if guide_only:
            return
        if channel == "terminal":
            live_channel = TerminalChannel()
        elif channel == "twilio":
            from bokken.interview.channels import ChannelUnavailable, TwilioChannel

            if not to:
                _fail("--channel twilio requires --to <E.164 number>", 2)
            try:
                live_channel = TwilioChannel(to)
            except ChannelUnavailable as exc:
                _fail(str(exc), 2)
        else:
            _fail(f"unknown channel {channel!r} (terminal, twilio)", 2)
        router = wiring.router_factory()(store)
        exchanges = run_validation_interview(
            store, router, guide, live_channel, participant=participant
        )
        out.print(
            f"journaled {exchanges} exchange(s); rerun `bokken export {name}` to refresh reports"
        )


@app.command("library")
@guarded
def library(
    product: Annotated[str | None, typer.Option(help="Filter by product key (repo path).")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Cross-run learnings: what earlier sessions supported, contradicted, or broke."""
    from bokken.library import read_learnings

    records = read_learnings(product)
    if as_json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
        return
    if not records:
        out.print("library is empty: finalize a run first")
        return
    for r in records:
        out.print(f"{r['session']} · {r['product'][:60]} · verdict {r['verdict'] or '-'}")
        for a in r["assumptions"]:
            if a["score"] != "untested":
                out.print(f"  [{a['score']}] {a['statement'][:100]}")


@app.command("costs")
@guarded
def costs(name: str, as_json: JsonFlag = False) -> None:
    """Cost report from the journaled model calls (list-price estimate)."""
    from bokken.dossier.model import build_model
    from bokken.report.context import cost_rows

    rows = cost_rows(build_model(resolve_session_dir(name)))
    total = round(sum(r["cost_usd"] for r in rows), 2)
    hit = sum(r["cache_read"] for r in rows)
    raw = sum(r["input"] for r in rows)
    payload = {
        "rows": rows,
        "total_usd": total,
        "cache_hit_rate": round(hit / (hit + raw), 3) if hit + raw else 0.0,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    out.print(
        f"{'stage':<10}{'prompt_id':<30}{'class':<11}{'calls':>6}{'input':>12}{'cached':>10}{'out':>8}{'~$':>8}"
    )
    for r in rows:
        out.print(
            f"{r['stage']:<10}{r['prompt_id']:<30}{r['class']:<11}{r['calls']:>6}"
            f"{r['input']:>12,}{r['cache_read']:>10,}{r['output']:>8,}{r['cost_usd']:>8.2f}"
        )
    out.print(f"total ~${total} (list prices) · cache hit rate {payload['cache_hit_rate']:.0%}")


@app.command("export")
@guarded
def export(name: str, as_json: JsonFlag = False) -> None:
    """Export the run report as a PowerPoint deck and a self-contained HTML page."""
    from bokken.report.generate import ReportError, generate_report

    try:
        pptx_path, html_path = generate_report(resolve_session_dir(name))
    except ReportError as err:
        _fail(str(err), 2)
        return
    result = contract.ExportResult(pptx_path=str(pptx_path), html_path=str(html_path))
    emit(
        result,
        as_json,
        lambda: out.print(f"report:\n  {pptx_path}\n  {html_path}"),
    )


@app.command("handoff")
@guarded
def handoff(name: str, as_json: JsonFlag = False) -> None:
    """Generate OpenSpec MVP specifications for the validated concept (the handoff)."""
    from bokken.handoff import HandoffRefusedError, generate_handoff

    session_dir = resolve_session_dir(name)
    try:
        generated = generate_handoff(session_dir, wiring.router_factory())
    except HandoffRefusedError as refusal:
        _fail(str(refusal), 2)
        return
    result = contract.HandoffResult(**generated)
    emit(
        result,
        as_json,
        lambda: out.print(f"handoff ({', '.join(result.capabilities)}):\n  {result.package_dir}"),
    )


@app.command("serve")
@guarded
def serve() -> None:
    """Expose the same core over MCP (stdio) for agents and IDEs."""
    from bokken.mcp.server import serve as mcp_serve

    mcp_serve()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
