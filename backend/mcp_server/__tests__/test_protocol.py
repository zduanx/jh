"""
In-memory MCP PROTOCOL tests (Phase 7B).

The tool tests (test_tools.py) call the functions directly. These tests instead
drive the server THROUGH THE REAL MCP PROTOCOL using the SDK's in-memory
client<->server transport (`create_connected_server_and_client_session`) — no
sockets, no Lambda, no flaky live server. This is the industry-standard way to
test an MCP server's wiring: it proves the tools are actually REGISTERED and
DISCOVERABLE, that their schemas serialize, and that a real `call_tool` round
trip returns structured content.

What this catches that direct calls cannot: a tool that's defined but not
decorated/registered, a signature the SDK can't turn into a JSON schema, or a
return value the protocol can't serialize.

Run: python3 -m pytest mcp_server/__tests__/test_protocol.py -v
"""
import time

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server.server import mcp
from mcp_server.__tests__.test_tools import make_job, make_resume

EXPECTED_TOOLS = {"search_jobs_semantic", "get_job", "get_resume", "score_against_jd"}


@pytest.mark.anyio
async def test_list_tools_exposes_all_four():
    """All four tools are registered and discoverable over the protocol."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        await client.initialize()
        resp = await client.list_tools()
        names = {t.name for t in resp.tools}
        assert EXPECTED_TOOLS <= names


@pytest.mark.anyio
async def test_tool_schemas_present():
    """Each tool advertises a description and an input schema (LLM-usable)."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        await client.initialize()
        tools = {t.name: t for t in (await client.list_tools()).tools}
        for name in EXPECTED_TOOLS:
            t = tools[name]
            assert t.description and len(t.description) > 20  # docstring carried through
            assert t.inputSchema and "properties" in t.inputSchema
        # spot-check that a documented param made it into the schema
        assert "company" in tools["search_jobs_semantic"].inputSchema["properties"]


@pytest.mark.anyio
async def test_call_get_resume_round_trip(mcp_db, seed_user):
    """A real call_tool round trip returns the tool's structured result."""
    make_resume(mcp_db, seed_user.user_id, text="Protocol resume", filename="p.pdf")

    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        await client.initialize()
        result = await client.call_tool("get_resume", {"user_id": seed_user.user_id})

    assert result.isError is False
    # FastMCP wraps the tool's return under "result" (the tool is typed dict|None,
    # so the SDK can't promise an object schema and wraps it like the list tools).
    payload = result.structuredContent["result"]
    assert payload["filename"] == "p.pdf"
    assert payload["text"] == "Protocol resume"


@pytest.mark.anyio
async def test_call_search_round_trip(mcp_db, fake_voyage, seed_user):
    """search_jobs_semantic over the protocol returns ranked rows."""
    make_resume(mcp_db, seed_user.user_id)
    make_job(mcp_db, seed_user.user_id, title="Protocol Engineer")

    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        await client.initialize()
        result = await client.call_tool(
            "search_jobs_semantic", {"user_id": seed_user.user_id, "limit": 5}
        )

    assert result.isError is False
    rows = result.structuredContent["result"]  # list-returning tools wrap in {"result": [...]}
    assert any(r["title"] == "Protocol Engineer" for r in rows)
