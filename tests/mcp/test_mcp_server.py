import json
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams
from typer.testing import CliRunner

from bokken.cli import wiring
from bokken.cli.app import app as cli_app
from bokken.journal import read_events, replay, resolve_session_dir
from bokken.mcp.server import mcp
from bokken.models import ModelRouter
from tests.stages.fake_provider import ScriptedProvider
from tests.stages.test_engines_e2e import BRIEF, make_inputs


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOKKEN_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        wiring, "router_factory", lambda: lambda store: ModelRouter(store, ScriptedProvider())
    )
    return tmp_path


@asynccontextmanager
async def connected():
    """In-memory client<->server pair, fully scoped inside one test task."""
    server = mcp._lowlevel_server
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        client_read, client_write = client_streams
        server_read, server_write = server_streams
        async with anyio.create_task_group() as tg:

            async def run_server() -> None:
                await server.run(
                    server_read,
                    server_write,
                    server.create_initialization_options(),
                    raise_exceptions=False,
                )

            tg.start_soon(run_server)
            async with ClientSession(client_read, client_write) as session:
                await session.initialize()
                yield session
            tg.cancel_scope.cancel()


def result_json(result) -> dict | list:
    assert not result.is_error, result.content
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured
    return json.loads(result.content[0].text)


_GROUNDED_QUESTIONS = (
    "which problem statement do we take forward",
    "which concept advances to prototype",
)


def brief_with_inputs(tmp_path: Path) -> dict:
    """Inputs live inside the workspace root: over MCP, client-supplied paths
    are confined to it (see `test_input_path_outside_root_is_refused`)."""
    return {**BRIEF, "inputs": make_inputs(tmp_path / "home")}


async def test_capabilities_listing() -> None:
    async with connected() as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert {
            "create_session_tool",
            "run_session",
            "step_session",
            "stop_session",
            "get_status",
            "list_sessions_tool",
            "resolve_gate",
            "request_loopback",
            "submit_input",
            "query_journal",
            "generate_dossier",
            "export_report",
            "cost_report",
        } <= tools
        templates = (await client.list_resource_templates()).resource_templates
        uris = {t.uri_template for t in templates}
        assert "bokken://sessions/{name}/status" in uris
        assert "bokken://sessions/{name}/journal" in uris
        assert "bokken://sessions/{name}/dossier" in uris


async def test_dojo_create_run_gate_loop(tmp_path: Path) -> None:
    async with connected() as client:
        created = result_json(
            await client.call_tool(
                "create_session_tool",
                {"name": "mcp-dojo", "brief": brief_with_inputs(tmp_path), "mode": "dojo"},
            )
        )
        assert created["stage"] == "intake"

        outcome = result_json(await client.call_tool("run_session", {"name": "mcp-dojo"}))
        assert outcome["halt"] == "gate_pending"
        status = result_json(await client.call_tool("get_status", {"name": "mcp-dojo"}))
        assert status["state"] == "gate_pending"

        while True:
            outcome = result_json(await client.call_tool("run_session", {"name": "mcp-dojo"}))
            if outcome["halt"] == "completed":
                break
            assert outcome["halt"] == "gate_pending"
            result_json(
                await client.call_tool(
                    "resolve_gate", {"name": "mcp-dojo", "resolution": "approve"}
                )
            )

        dossier = result_json(await client.call_tool("generate_dossier", {"name": "mcp-dojo"}))
        assert dossier["status"] == "complete"
        resource = await client.read_resource("bokken://sessions/mcp-dojo/dossier")
        assert json.loads(resource.contents[0].text)["status"] == "complete"


async def test_client_input_paths_are_confined_to_the_workspace(tmp_path: Path) -> None:
    """The MCP caller is untrusted: its brief cannot name files outside the root."""
    outside = tmp_path / "victim"
    outside.mkdir()
    (outside / "notes.md").write_text("the launch codes\n")
    root = tmp_path / "home"
    root.mkdir(parents=True, exist_ok=True)
    suffixless = root / "id_rsa"
    suffixless.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nhunter2\n")

    async with connected() as client:
        cases = {
            # a named file outside the text allowlist is refused, not read
            "suffix": {"documents": [str(suffixless)]},
            # traversal out of the root
            "traversal": {"documents": ["../victim/notes.md"]},
            # absolute path outside the root
            "absolute": {"documents": [str(outside / "notes.md")]},
            # a symlink inside the root pointing out of it
            "symlink": {"documents": ["escape.md"]},
        }
        (root / "escape.md").symlink_to(outside / "notes.md")
        for label, inputs in cases.items():
            refused = await client.call_tool(
                "create_session_tool",
                {"name": f"refused-{label}", "brief": {**BRIEF, "inputs": inputs}},
            )
            assert refused.is_error, label
            message = refused.content[0].text
            assert "allowlist" in message or "outside the authorized input root" in message, label
        assert not list((root / "sessions").glob("refused-*"))


async def test_operator_can_widen_the_input_root(tmp_path: Path, monkeypatch) -> None:
    elsewhere = tmp_path / "research"
    elsewhere.mkdir()
    note = elsewhere / "interview.md"
    note.write_text("I stopped riding because arrivals were unpredictable.\n")
    monkeypatch.setenv("BOKKEN_INPUT_ROOTS", str(elsewhere))

    async with connected() as client:
        created = result_json(
            await client.call_tool(
                "create_session_tool",
                {"name": "widened", "brief": {**BRIEF, "inputs": {"discussions": [str(note)]}}},
            )
        )
        assert created["stage"] == "intake"
        event = next(e for e in read_events(resolve_session_dir("widened")))
        assert event.payload["brief"]["inputs"]["discussions"] == [str(note.resolve())]
        assert event.payload["config"]["panel"]["input_roots"] == [str(elsewhere.resolve())]


async def test_duplicate_create_is_tool_error(tmp_path: Path) -> None:
    async with connected() as client:
        args = {"name": "dup", "brief": brief_with_inputs(tmp_path)}
        assert not (await client.call_tool("create_session_tool", args)).is_error
        result = await client.call_tool("create_session_tool", args)
        assert result.is_error
        assert "already exists" in result.content[0].text


async def test_gate_attribution_is_from_handshake_not_arguments(tmp_path: Path) -> None:
    async with connected() as client:
        await client.call_tool(
            "create_session_tool", {"name": "attr", "brief": brief_with_inputs(tmp_path)}
        )
        await client.call_tool("run_session", {"name": "attr"})
        forged = await client.call_tool(
            "resolve_gate",
            {"name": "attr", "resolution": "approve", "actor": {"kind": "human", "name": "boss"}},
        )
        if forged.is_error:  # forged arg rejected by schema: resolve legitimately
            result = await client.call_tool(
                "resolve_gate", {"name": "attr", "resolution": "approve"}
            )
            assert not result.is_error
        events = list(read_events(resolve_session_dir("attr")))
        resolved = next(e for e in events if e.type == "session.gate_resolved")
        assert resolved.actor.kind == "agent"
        assert resolved.actor.name and resolved.actor.name != "boss"


async def test_stale_input_is_refused(tmp_path: Path) -> None:
    async with connected() as client:
        await client.call_tool(
            "create_session_tool",
            {"name": "founder-mcp", "brief": BRIEF, "mode": "founder", "gate_policy": "none"},
        )
        outcome = result_json(await client.call_tool("run_session", {"name": "founder-mcp"}))
        assert outcome["halt"] == "input_pending"
        qid = outcome["pending_question_id"]

        stale = await client.call_tool(
            "submit_input", {"name": "founder-mcp", "question_id": "bogus", "answer": "x"}
        )
        assert stale.is_error and "no pending question" in stale.content[0].text

        stored = result_json(
            await client.call_tool(
                "submit_input",
                {
                    "name": "founder-mcp",
                    "question_id": qid,
                    "answer": "arrivals were unpredictable",
                },
            )
        )
        assert stored["stored"] is True
        outcome = result_json(await client.call_tool("run_session", {"name": "founder-mcp"}))
        assert outcome["halt"] in ("input_pending", "completed")


async def test_handoff_tool_and_finalization(tmp_path: Path) -> None:
    async with connected() as client:
        await client.call_tool(
            "create_session_tool",
            {
                "name": "handoff-mcp",
                "brief": brief_with_inputs(tmp_path),
                "mode": "dojo",
                "gate_policy": "none",
            },
        )
        outcome = result_json(await client.call_tool("run_session", {"name": "handoff-mcp"}))
        assert outcome["halt"] == "completed"
        # Completion finalizes automatically: dossier + handoff specs.
        assert "handoff specs generated" in outcome["finalization"]
        session_dir = resolve_session_dir("handoff-mcp")
        assert (session_dir / "dossier" / "dossier.md").exists()
        assert (session_dir / "handoff" / "traceability.json").exists()
        # Explicit regeneration returns the contract shape.
        regenerated = result_json(
            await client.call_tool("generate_handoff", {"name": "handoff-mcp"})
        )
        assert regenerated["capabilities"] == ["schedule-publication"]
        assert regenerated["change_id"].startswith("build-mvp-")


async def test_journal_parity_with_cli(tmp_path: Path) -> None:
    async with connected() as client:
        await client.call_tool(
            "create_session_tool",
            {
                "name": "parity",
                "brief": brief_with_inputs(tmp_path),
                "mode": "dojo",
                "gate_policy": "none",
            },
        )
        outcome = result_json(await client.call_tool("run_session", {"name": "parity"}))
        assert outcome["halt"] == "completed"

        via_mcp = result_json(
            await client.call_tool(
                "query_journal", {"name": "parity", "type": "option", "stage": "ideate"}
            )
        )
        cli = CliRunner().invoke(
            cli_app, ["journal", "parity", "--type", "option", "--stage", "ideate", "--json"]
        )
        via_cli = [json.loads(line) for line in cli.stdout.strip().splitlines()]
        assert via_mcp == via_cli


async def test_submitted_input_is_attributed_to_the_client_not_the_founder(tmp_path: Path) -> None:
    """An answer an agent types over MCP is that agent's, never human testimony."""
    fabricated = "AGENT-FABRICATED: riders churn because arrivals are unpredictable"
    async with connected() as client:
        await client.call_tool(
            "create_session_tool",
            {"name": "attr-input", "brief": BRIEF, "mode": "founder", "gate_policy": "none"},
        )
        outcome = result_json(await client.call_tool("run_session", {"name": "attr-input"}))
        assert outcome["halt"] == "input_pending"

        forged = await client.call_tool(
            "submit_input",
            {
                "name": "attr-input",
                "question_id": outcome["pending_question_id"],
                "answer": fabricated,
                "actor": {"kind": "human", "name": "founder"},
            },
        )
        if forged.is_error:  # forged arg rejected by schema: submit legitimately
            result_json(
                await client.call_tool(
                    "submit_input",
                    {
                        "name": "attr-input",
                        "question_id": outcome["pending_question_id"],
                        "answer": fabricated,
                    },
                )
            )
        # Consume that answer, then drive the rest of the run to completion.
        for _ in range(40):
            outcome = result_json(await client.call_tool("run_session", {"name": "attr-input"}))
            if outcome["halt"] != "input_pending":
                break
            result_json(
                await client.call_tool(
                    "submit_input",
                    {
                        "name": "attr-input",
                        "question_id": outcome["pending_question_id"],
                        "answer": "supported: agent-supplied filler",
                    },
                )
            )
        assert outcome["halt"] == "completed"

    events = list(read_events(resolve_session_dir("attr-input")))
    captured = [
        e for e in events if e.type == "evidence.captured" and e.payload["content"] == fabricated
    ]
    assert captured, "the submitted answer was never journaled as evidence"
    evidence = captured[0]
    # Attribution: the handshake client, never the founder, never a human.
    assert evidence.actor.kind == "agent"
    assert evidence.actor.name != "founder"
    # Honesty: machine text is simulated, and never labeled a founder interview.
    assert evidence.payload["confidence_class"] == "simulated"
    assert "founder interview" not in evidence.payload["source"]
    # Nothing in an agent-driven session may pose as human participation.
    assert not [e for e in events if e.actor.kind == "human"]

    # The class propagates: decisions resting on that evidence inherit the flag.
    state = replay(events)
    flagged = [d for d in state.decisions.values() if d.question in _GROUNDED_QUESTIONS]
    assert flagged and all(d.requires_real_validation for d in flagged)


async def test_agent_supplied_evidence_is_labeled_synthetic_in_the_dossier(tmp_path: Path) -> None:
    from bokken.dossier.model import build_model

    async with connected() as client:
        await client.call_tool(
            "create_session_tool",
            {"name": "synth-label", "brief": BRIEF, "mode": "founder", "gate_policy": "none"},
        )
        outcome = result_json(await client.call_tool("run_session", {"name": "synth-label"}))
        for _ in range(40):
            if outcome["halt"] != "input_pending":
                break
            result_json(
                await client.call_tool(
                    "submit_input",
                    {
                        "name": "synth-label",
                        "question_id": outcome["pending_question_id"],
                        "answer": "untested: agent-supplied filler",
                    },
                )
            )
            outcome = result_json(await client.call_tool("run_session", {"name": "synth-label"}))
        assert outcome["halt"] == "completed"

    model = build_model(resolve_session_dir("synth-label"))
    answered = [e for e in model.evidence.values() if "agent-supplied" in e.source]
    assert answered and all(e.synthetic for e in answered)
    # No interview evidence in an agent-driven run escapes the synthetic label.
    interview = [e for e in model.evidence.values() if e.stage == "empathize"]
    assert interview and all(e.synthetic for e in interview)
