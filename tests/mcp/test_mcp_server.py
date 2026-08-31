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
from bokken.journal import read_events, resolve_session_dir
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


def brief_with_inputs(tmp_path: Path) -> dict:
    return {**BRIEF, "inputs": make_inputs(tmp_path)}


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
