"""The bokken CLI: barista-style lifecycle verbs over durable, resumable sessions."""

from __future__ import annotations

import functools
import json
import os
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, NoReturn

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
from bokken.journal.query import _type_matches
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


def _fail(message: str, code: int) -> NoReturn:
    print(message, file=sys.stderr)
    raise typer.Exit(code)


def guarded(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except typer.BadParameter:  # a clean usage error, not an unexpected one
            raise
        except KeyboardInterrupt:
            print("interrupted; the session is resumable with `bokken run`", file=sys.stderr)
            raise typer.Exit(0) from None
        except _REFUSED as exc:
            _fail(str(exc), 2)
        except Exception as exc:  # unexpected
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


def _csv_list(text: str) -> list[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


def _review_brief(brief_data: dict) -> None:
    """Interactive review of the three fields a brief hinges on; each prompt
    shows the drafted value as its default."""
    brief_data["problem_space"] = typer.prompt("Problem space", default=brief_data["problem_space"])
    segments = typer.prompt(
        "Target segments (comma-separated)", default=", ".join(brief_data["target_segments"])
    )
    brief_data["target_segments"] = _csv_list(segments)
    criteria = typer.prompt(
        "Success criteria (comma-separated)", default=", ".join(brief_data["success_criteria"])
    )
    brief_data["success_criteria"] = _csv_list(criteria)


@app.command("version")
def version(as_json: JsonFlag = False) -> None:
    """Print the bokken version."""
    if as_json:
        print(json.dumps({"version": bokken.__version__}))
        return
    print(bokken.__version__)


@app.command("init")
@guarded
def init(
    template: Annotated[
        str | None,
        typer.Option(help="saas-retention, consumer-app, or internal-tool (skips prompts)."),
    ] = None,
    from_repo: Annotated[
        Path | None,
        typer.Option(
            "--from-repo",
            help="Draft the brief from this repository (two model calls, ~$0.10-0.30).",
        ),
    ] = None,
    metrics: Annotated[
        list[Path] | None,
        typer.Option(help="Metrics file to ground the draft (with --from-repo)."),
    ] = None,
    yes: Annotated[
        bool, typer.Option("--yes", help="Accept the drafted brief without prompts.")
    ] = False,
    out_path: Annotated[Path, typer.Option("--out", help="Where to write the brief JSON.")] = Path(
        "bokken-brief.json"
    ),
    as_json: JsonFlag = False,
) -> None:
    """Write a validated brief file from a template or drafted from your repo."""
    from bokken.cli.templates import TEMPLATES, build_brief

    if as_json and template is None and from_repo is None:
        _fail("--json needs --template or --from-repo; interactive prompts are disabled", 2)
    drafting_cost: float | None = None
    if from_repo is not None:
        from bokken.cli.autopilot import BriefDraftError, draft_brief_from_repo

        try:
            brief_data, drafting_cost = draft_brief_from_repo(
                from_repo, metrics or [], wiring.router_factory()
            )
        except BriefDraftError as exc:
            _fail(str(exc), 2)
        if not yes and not as_json:
            out.print(f"drafted from {from_repo} (drafting cost ~${drafting_cost:.2f}); review:")
            _review_brief(brief_data)
    elif template is not None:
        if template not in TEMPLATES:
            raise typer.BadParameter(f"unknown template; pick one of {sorted(TEMPLATES)}")
        brief_data = build_brief(template)
    else:
        names = sorted(TEMPLATES)
        out.print("Templates: " + ", ".join(f"{i + 1}) {n}" for i, n in enumerate(names)))
        pick = typer.prompt("Template", default="1").strip()
        if pick.isdigit():
            if not 1 <= int(pick) <= len(names):
                raise typer.BadParameter(f"template number must be between 1 and {len(names)}")
            chosen = names[int(pick) - 1]
        else:
            chosen = pick
        if chosen not in TEMPLATES:
            raise typer.BadParameter(f"unknown template; pick one of {names}")
        product = typer.prompt("Product name")
        brief_data = build_brief(chosen, product)
        _review_brief(brief_data)
        repo = typer.prompt("Path to the product's repo (empty to skip)", default="")
        if repo.strip():
            brief_data["inputs"]["repo"] = str(Path(repo.strip()).expanduser().resolve())

    Brief.model_validate(brief_data)  # fail before touching disk
    out_path.write_text(json.dumps(brief_data, indent=2, ensure_ascii=False) + "\n")
    session = out_path.stem.removesuffix("-brief") or "my-product"
    if as_json:
        print(
            json.dumps(
                {
                    "brief": str(out_path),
                    "template": template or ("from-repo" if from_repo else "interactive"),
                    "drafting_cost_usd": drafting_cost,
                }
            )
        )
        return
    if drafting_cost is not None:
        out.print(f"drafting cost: ~${drafting_cost:.2f} list price (journal discarded)")
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
    theme: Annotated[
        str | None, typer.Option(help="Report theme journaled for this session's exports.")
    ] = None,
    panel_size: Annotated[int, typer.Option(help="Synthetic panel size (dojo).")] = 6,
    seed: Annotated[int, typer.Option(help="Panel casting seed.")] = 7,
    as_json: JsonFlag = False,
) -> None:
    """Create a session: validate the brief, journal it, enter intake."""
    if brief is not None:
        try:
            brief_data = json.loads(brief.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail(f"--brief file {brief} is not valid JSON: {exc}", 2)
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

    if theme is not None:
        from bokken.report.theme import BUILTIN

        theme_path = Path(theme).expanduser()
        if theme not in BUILTIN and theme_path.exists():
            # Journal file themes as absolute paths: export must not depend
            # on the cwd `bokken new` happened to run from.
            theme = str(theme_path.resolve())

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
            **({"report_theme": theme} if theme else {}),
            **session_model_config(provider, model, reasoning_effort),
        },
    )
    result = contract.status_for_dir(name, session_dir)
    emit(result, as_json, lambda: out.print(f"created session '{name}' at {session_dir}"))


def _session_receipt(session_dir: Path) -> tuple[float, int]:
    """Session-to-date list-price cost and model-call count from the journal."""
    from bokken.dossier.model import build_model
    from bokken.report.context import cost_rows

    rows = cost_rows(build_model(session_dir))
    return round(sum(r["cost_usd"] for r in rows), 2), sum(r["calls"] for r in rows)


def _budget_guardrail(session_dir: Path) -> int | None:
    from bokken.journal.workspace import session_config

    return session_config(session_dir).get("budgets", {}).get("total_tokens")


def _session_is_demo(session_dir: Path) -> bool:
    from bokken.journal.workspace import session_config

    return bool(session_config(session_dir).get("demo"))


@app.command("run")
@guarded
def run(name: str, as_json: JsonFlag = False) -> None:
    """Resume and continue the loop until a gate, input, stop, or completion.
    Completed runs are finalized automatically: Dossier, then handoff specs."""
    session_dir = resolve_session_dir(name)
    if not as_json:
        guardrail = _budget_guardrail(session_dir)
        limit = f"stops at {guardrail:,} tokens" if guardrail else "no token guardrail set"
        out.print(f"cost framing: a full run typically lands at $20-35 list price; {limit}")
    runner = wiring.build_runner(session_dir, interactive=not as_json)
    result = _run_result(runner.run(actor=HUMAN))
    if result.halt == "completed":
        from bokken.handoff import finalize_session

        finalization = finalize_session(session_dir, wiring.session_router_factory(session_dir))
        result = result.model_copy(update={"finalization": finalization.summary()})
    cost, calls = _session_receipt(session_dir)
    result = result.model_copy(update={"cost_usd": cost, "model_calls": calls})

    def _text() -> None:
        _print_run(result)
        out.print(
            f"receipt: ${cost:.2f} across {calls} model calls so far "
            f"(bokken costs {name} for the breakdown)"
        )

    emit(result, as_json, _text)


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
def stop(
    name: str,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Stop the run (journaled as a human stop). The session stays resumable."""
    runner = wiring.build_runner(resolve_session_dir(name), interactive=False)
    runner.stop(actor=HUMAN, detail=reason)
    if as_json:
        print(json.dumps({"stopped": name, "reason": reason, "resumable": True}))
        return
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


@app.command("backlog")
@guarded
def backlog(
    name: str,
    fmt: Annotated[
        str | None,
        typer.Option("--format", help="Export as 'csv' or 'markdown' (issue-tracker checklist)."),
    ] = None,
    as_json: JsonFlag = False,
) -> None:
    """Ranked, exportable validation to-do from the assumption register and research debt."""
    from bokken.backlog import build_backlog, to_csv, to_markdown

    if fmt is not None and fmt not in ("csv", "markdown"):
        _fail("--format must be 'csv' or 'markdown'", 2)
    session_dir = resolve_session_dir(name)
    result = build_backlog(session_dir, name)
    if fmt == "csv":
        print(to_csv(result), end="")
        return
    if fmt == "markdown":
        print(to_markdown(result), end="")
        return

    def human() -> None:
        from rich.table import Table

        if result.banner:
            out.print(result.banner)
        table = Table(title=f"Validation backlog: {result.name}")
        for col in ("rank", "kind", "impact", "uncertainty", "confidence", "source", "statement"):
            table.add_column(col)
        for it in result.items:
            table.add_row(
                str(it.rank),
                it.kind,
                it.impact or "-",
                it.uncertainty or "-",
                it.confidence_class,
                it.source,
                it.statement,
            )
        if not result.items:
            out.print("no untested or contradicted assumptions and no open research debt")
        else:
            out.print(table)
        out.print(result.flip_the_verdict)

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


def _parse_since(since: str | None) -> tuple[int | None, datetime | None]:
    """--since accepts a seq number or an ISO timestamp (naive = UTC)."""
    if since is None:
        return None, None
    if since.isdigit():
        return int(since), None
    try:
        ts = datetime.fromisoformat(since)
    except ValueError:
        _fail(f"--since must be a seq number or an ISO timestamp, got {since!r}", 2)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return None, ts


def _matches(
    event: Any,
    type_filter: str | None,
    stage: str | None,
    actor: str | None,
    since_ts: datetime | None = None,
) -> bool:
    if since_ts is not None and event.ts < since_ts:
        return False
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
def demo(
    name: Annotated[str, typer.Argument(help="Session name for the demo run.")] = "demo",
    as_json: JsonFlag = False,
) -> None:
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
    cost, calls = _session_receipt(summary["session_dir"])
    out.print(
        f"you were charged $0.00 - 0 network calls, 0 real tokens; the journaled "
        f"usage is an illustrative live-run profile: ~${cost:.0f} list price across "
        f"{calls} calls (`bokken costs {name}` for the lane-by-lane math)"
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
    as_json: JsonFlag = False,
    to: Annotated[
        str | None, typer.Option(help="Phone for --channel twilio (E.164); never journaled.")
    ] = None,
) -> None:
    """Run a real validation interview against the session's research debt."""
    from bokken.interview import build_guide, run_validation_interview
    from bokken.interview.channels import ChannelUnavailable, TerminalChannel
    from bokken.interview.guide import journal_guide
    from bokken.journal.store import JournalStore

    session_dir = resolve_session_dir(name)
    with JournalStore.open(session_dir) as store:
        guide = build_guide(store)
        if guide.empty:
            _fail("nothing to validate: no research debt and no untested assumptions", 2)
        path = journal_guide(store, guide)
        if not as_json:
            out.print(f"guide: {session_dir / path}")
        if guide_only:
            if as_json:
                print(json.dumps({"guide": str(session_dir / path), "exchanges": 0}))
            return
        if channel == "terminal":
            live_channel = TerminalChannel()
        elif channel == "twilio":
            from bokken.interview.channels import TwilioChannel

            if not to:
                _fail("--channel twilio requires --to <E.164 number>", 2)
            try:
                live_channel = TwilioChannel(to)
            except ChannelUnavailable as exc:
                _fail(str(exc), 2)
        else:
            _fail(f"unknown channel {channel!r} (terminal, twilio)", 2)
        router = wiring.router_factory()(store)
        try:
            exchanges = run_validation_interview(
                store, router, guide, live_channel, participant=participant
            )
        except ChannelUnavailable as exc:
            # Consent refused (declined, no reply, or ambiguous) is journaled by
            # the engine; the operator gets the reason, not a stack trace.
            _fail(str(exc), 2)
        if as_json:
            print(json.dumps({"guide": str(session_dir / path), "exchanges": exchanges}))
            return
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


@app.command("diff")
@guarded
def diff(
    old: Annotated[str, typer.Argument(help="The earlier finalized run.")],
    new: Annotated[str, typer.Argument(help="The later finalized run.")],
    as_json: JsonFlag = False,
) -> None:
    """Compare two finalized runs of the same product: what moved between them.

    Pure derivation - no model calls. Reports Ulwick opportunity re-ranking,
    assumptions that flipped status, current-capability changes, and the verdict
    change. Statements are matched across runs by their (whitespace-stripped)
    text, so a reworded statement reads as an add plus a drop, not a change.
    Refuses (exit 2) if either run is unfinalized or they differ in product."""
    from bokken.diffing import DiffRefused, diff_sessions

    old_dir = resolve_session_dir(old)
    new_dir = resolve_session_dir(new)
    try:
        data = diff_sessions(old_dir, new_dir)
    except DiffRefused as refusal:
        _fail(str(refusal), 2)
    result = contract.diff_result(data)

    def line(text: str) -> None:
        # markup off: run tags like [both] and class tags like [simulated] are
        # literal text, not Rich style markup.
        out.print(text, markup=False, highlight=False)

    def human() -> None:
        line(f"diff {result.old_session} -> {result.new_session} (product {result.product})")
        line("opportunities:")
        if not result.opportunities:
            line("  (none)")
        for o in result.opportunities:
            if o.run == "both":
                delta = f" (delta {o.score_delta:+g})" if o.score_delta is not None else ""
                line(
                    f"  [both] {o.statement}: {o.old_score} -> {o.new_score}{delta}, "
                    f"{o.old_band} -> {o.new_band} [{o.confidence_class}]"
                )
            elif o.run == "new":
                line(
                    f"  [new] added: {o.statement}: {o.new_score} ({o.new_band}) "
                    f"[{o.confidence_class}]"
                )
            else:
                line(
                    f"  [old] dropped: {o.statement}: {o.old_score} ({o.old_band}) "
                    f"[{o.confidence_class}]"
                )
        line("assumptions:")
        if not result.assumptions:
            line("  (none)")
        for a in result.assumptions:
            if a.run == "both":
                line(
                    f"  [both] {a.statement}: {a.old_score} -> {a.new_score} [{a.confidence_class}]"
                )
            elif a.run == "new":
                line(f"  [new] added: {a.statement}: {a.new_score} [{a.confidence_class}]")
            else:
                line(f"  [old] dropped: {a.statement}: {a.old_score} [{a.confidence_class}]")
        line("capabilities:")
        if not result.capabilities:
            line("  (none)")
        for c in result.capabilities:
            line(f"  [{c.run}] {c.change}: {c.statement} [{c.confidence_class}]")
        line("verdict:")
        if result.verdict is None:
            line("  (none)")
        else:
            v = result.verdict
            marker = "changed" if v.changed else "unchanged"
            line(
                f"  {v.old_verdict} [{v.old_confidence_class}] -> "
                f"{v.new_verdict} [{v.new_confidence_class}] ({marker})"
            )

    emit(result, as_json, human)


@app.command("pack")
@guarded
def pack(
    name: str,
    deliverables_only: Annotated[
        bool,
        typer.Option(
            "--deliverables-only",
            help="Omit journal, evidence graph, and artifacts (for external sharing).",
        ),
    ] = False,
    out_path: Annotated[
        Path | None, typer.Option("--out", help="Target zip path (default: <name>.bokken.zip).")
    ] = None,
    as_json: JsonFlag = False,
) -> None:
    """Pack a finalized session into one portable archive with a manifest."""
    from bokken.bundle import PackError, pack_session

    session_dir = resolve_session_dir(name)
    try:
        bundle = pack_session(session_dir, deliverables_only=deliverables_only, out=out_path)
    except PackError as exc:
        _fail(str(exc), 2)
    size = bundle.stat().st_size
    if as_json:
        print(
            json.dumps(
                {
                    "bundle": str(bundle),
                    "bytes": size,
                    "contents": "deliverables-only" if deliverables_only else "full",
                }
            )
        )
        return
    detail = "deliverables only" if deliverables_only else "full: journal + evidence graph included"
    out.print(f"packed: {bundle} ({size / 1024:.0f} KB, {detail})")


@app.command("costs")
@guarded
def costs(name: str, as_json: JsonFlag = False) -> None:
    """Cost report from the journaled model calls (list-price estimate)."""
    session_dir = resolve_session_dir(name)
    payload = contract.cost_payload(session_dir)
    rows = payload["rows"]
    total = payload["total_usd"]
    rollup = payload["rollup"]
    grounding = payload["grounding"]
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
    out.print(
        f"exploration ~${rollup['exploration']:.2f} (reading the product: code map, UI, retrieval)"
    )
    out.print(
        f"research    ~${rollup['research']:.2f} "
        "(learning from people: interviews, outcomes, validation)"
    )
    out.print(f"synthesis   ~${rollup['synthesis']:.2f} (framing, ideating, prototyping, deciding)")
    out.print(
        f"persona turns {grounding['persona_turns']} · abstentions "
        f"{grounding['abstentions']} · citation-invalid "
        f"{grounding['citation_invalid_abstentions']} "
        f"({grounding['citation_invalid_rate']:.0%} of turns)"
    )
    if _session_is_demo(session_dir):
        out.print("demo session: illustrative usage - you were charged $0.00")


@app.command("opportunities")
@guarded
def opportunities(name: str, as_json: JsonFlag = False) -> None:
    """Segment x outcome opportunity matrix (Ulwick/ODI), derived from the journal.

    Which segment is most underserved on which desired outcome. A pure derivation
    from the replayed per-persona outcome scores - no model calls. Each cell shows
    the mean Ulwick opportunity score and the sample size behind it; a cell with
    fewer than two personas is flagged low-confidence.
    """
    from bokken.dossier.model import build_model
    from bokken.report.context import build_opportunity_matrix

    session_dir = resolve_session_dir(name)
    matrix = build_opportunity_matrix(session_dir, build_model(session_dir))
    if matrix is None:
        _fail(
            f"session '{name}' has no scored desired outcomes: "
            "no opportunity matrix to show (run Empathize to score outcomes first)",
            2,
        )

    def human() -> None:
        if matrix.simulated:
            out.print(
                "simulated run: this matrix is scored by a synthetic persona panel "
                "and requires validation with real users."
            )
        out.print(
            "Underserved by segment (Ulwick: Opp = Importance + max(Importance - Satisfaction, 0); "
            "each cell shows score and sample size n; * = low confidence, n<2)"
        )
        width = max([7, *map(len, matrix.segments)])
        header = f"{'segment':<{width}}" + "".join(
            f"{f'O{i}':>12}" for i in range(len(matrix.outcomes))
        )
        out.print(header)

        def cell_text(segment: str, outcome: str) -> str:
            cell = matrix.cell(segment, outcome)
            if cell is None:
                return f"{'-':>12}"
            flag = "*" if cell.low_confidence else ""
            return f"{f'{cell.score} (n{cell.n}){flag}':>12}"

        for segment in matrix.segments:
            cells = (cell_text(segment, outcome) for outcome in matrix.outcomes)
            out.print(f"{segment:<{width}}" + "".join(cells))
        for i, outcome in enumerate(matrix.outcomes):
            out.print(f"O{i}: {outcome}")

    emit(matrix, as_json, human)


@app.command("estimate")
@guarded
def estimate(
    brief: Annotated[Path, typer.Argument(help="Brief as a JSON file.")],
    panel_size: Annotated[
        int, typer.Option(help="Panel size to model (matches `bokken new`).")
    ] = 6,
    provider: Annotated[str, typer.Option(help="anthropic or openai")] = "anthropic",
    model: Annotated[
        str | None, typer.Option(help="Use this model for frontier routing classes.")
    ] = None,
    as_json: JsonFlag = False,
) -> None:
    """Predict a run's cost + tokens before creating a session (modeled estimate).

    Pure derivation - no session, no model call, no network, no journal. The
    figure is a modeled estimate from an illustrative profile, not a
    measurement; once a run exists, `bokken costs` reports the actual list
    price."""
    from bokken.estimate import estimate_run

    # Load and validate the brief before any derivation; a missing or
    # schema-invalid file exits 2 with a stderr message and writes nothing.
    try:
        brief_data = json.loads(brief.read_text(encoding="utf-8"))
    except OSError as exc:
        _fail(f"cannot read brief file {brief}: {exc}", 2)
    except json.JSONDecodeError as exc:
        _fail(f"brief file {brief} is not valid JSON: {exc}", 2)
    Brief.model_validate(brief_data)  # schema-invalid brief -> guarded exits 2

    est = estimate_run(panel_size, provider=provider, model=model)
    result = contract.estimate_result(est)
    emit(result, as_json, lambda: _print_estimate(result))


def _print_estimate(result: contract.EstimateResult) -> None:
    where = f"provider {result.provider}" + (f", model {result.model}" if result.model else "")
    out.print(
        f"modeled estimate: ${result.cost_low_usd:.2f}-${result.cost_high_usd:.2f} "
        f"(point ~${result.cost_point_usd:.2f}, list prices) · {where}"
    )
    out.print(f"{'lane':<12}{'calls':>7}{'tokens':>12}{'~$':>10}")
    for lane in result.lanes:
        out.print(f"{lane.lane:<12}{lane.calls:>7}{lane.tokens:>12,}{lane.cost_usd:>10.2f}")
    out.print(
        f"{'total':<12}{result.total_calls:>7}{result.total_tokens:>12,}"
        f"{result.cost_point_usd:>10.2f}"
    )
    for line in result.assumptions:
        out.print(f"- {line}")
    out.print(result.caveat)


@app.command("export")
@guarded
def export(
    name: str,
    theme: Annotated[
        str | None,
        typer.Option(help="Report theme: bokken, plain, or a theme JSON path."),
    ] = None,
    as_json: JsonFlag = False,
) -> None:
    """Export the run report as a PowerPoint deck and a self-contained HTML page."""
    from bokken.report.generate import ReportError, generate_report
    from bokken.report.theme import ThemeError

    try:
        pptx_path, html_path = generate_report(resolve_session_dir(name), theme_spec=theme)
    except (ThemeError, ReportError) as err:
        _fail(str(err), 2)
    result = contract.ExportResult(pptx_path=str(pptx_path), html_path=str(html_path))
    emit(
        result,
        as_json,
        lambda: out.print(f"report:\n  {pptx_path}\n  {html_path}"),
    )


@app.command("handoff")
@guarded
def handoff(
    name: str,
    emit_targets: Annotated[
        list[str] | None,
        typer.Option(
            "--emit",
            help="Also render an executable adapter: claude-code, cursor, or codex (repeatable).",
        ),
    ] = None,
    as_json: JsonFlag = False,
) -> None:
    """Generate OpenSpec MVP specifications for the validated concept (the handoff)."""
    from bokken.handoff import (
        HandoffFormatError,
        HandoffGenerationError,
        HandoffRefusedError,
        generate_handoff,
    )
    from bokken.handoff.emit import EmitError, emit_adapters

    session_dir = resolve_session_dir(name)
    try:
        generated = generate_handoff(session_dir, wiring.session_router_factory(session_dir))
    except (HandoffRefusedError, HandoffGenerationError, HandoffFormatError) as refusal:
        _fail(str(refusal), 2)
    adapter_paths: list[str] = []
    if emit_targets:
        try:
            adapter_paths = [str(p) for p in emit_adapters(session_dir, emit_targets)]
        except EmitError as exc:
            _fail(str(exc), 2)
    result = contract.HandoffResult(**generated, adapters=adapter_paths)
    emit(
        result,
        as_json,
        lambda: out.print(
            f"handoff ({', '.join(result.capabilities)}):\n  {result.package_dir}"
            + ("".join(f"\n  adapter: {a}" for a in adapter_paths))
        ),
    )


@app.command("doctor")
def doctor(
    network: Annotated[
        bool, typer.Option("--network", help="Also probe provider reachability.")
    ] = False,
    as_json: JsonFlag = False,
) -> None:
    """Diagnose the environment: keys, extras, browser, workspace - with fixes."""
    from bokken.cli.doctor import run_checks

    checks = run_checks(network=network)
    ok = all(c.ok for c in checks)
    if as_json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "checks": [
                        {"name": c.name, "ok": c.ok, "detail": c.detail, "fix": c.fix}
                        for c in checks
                    ],
                }
            )
        )
        return
    for c in checks:
        mark = "ok " if c.ok else "!! "
        out.print(f"{mark}{c.name:<22} {c.detail}", markup=False, highlight=False)
        if c.fix:
            out.print(f"   fix: {c.fix}", markup=False, highlight=False)
    if ok:
        out.print("everything needed for a real run is in place")
    else:
        out.print("apply the fixes above, then re-run `bokken doctor`")


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
