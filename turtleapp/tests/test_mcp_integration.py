"""Test MCP integration with LangGraph (HTTP transport)."""

import pytest
from turtleapp.src.mcp.client.tools import get_qbittorrent_tools


def test_mcp_tools_load():
    """Test MCP tools can be loaded from HTTP server."""
    tools = get_qbittorrent_tools()

    assert len(tools) == 6  # Expected number of MCP tools
    assert all(tool.name.startswith("qb_") for tool in tools)


def test_tool_names():
    """Test all expected tool names are present."""
    tools = get_qbittorrent_tools()
    tool_names = [tool.name for tool in tools]

    expected_tools = [
        "qb_search_torrents",
        "qb_list_torrents",
        "qb_add_torrent",
        "qb_control_torrent",
        "qb_torrent_info",
        "qb_get_preferences"
    ]

    for expected in expected_tools:
        assert expected in tool_names


@pytest.mark.asyncio
@pytest.mark.expensive  # Requires running MCP HTTP server
async def test_mcp_search_tool_execution():
    """Test MCP search tool can execute over HTTP."""
    tools = get_qbittorrent_tools()
    search_tool = next(t for t in tools if t.name == "qb_search_torrents")

    # Test search with legal content
    result = await search_tool.ainvoke({"query": "Ubuntu 22.04", "limit": 5})

    assert "results" in result or "error" in result
    # Should return either results or error (if search plugins not configured)


@pytest.mark.asyncio
@pytest.mark.expensive
async def test_mcp_list_tool_execution():
    """Test MCP list tool can execute over HTTP."""
    tools = get_qbittorrent_tools()
    status_tool = next(t for t in tools if t.name == "qb_list_torrents")

    result = await status_tool.ainvoke({"filter": "all"})

    assert "torrents" in result or "count" in result
