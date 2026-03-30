"""Test agents using MCP tools (HTTP transport)."""

import pytest
from application.agents.nodes import create_torrent_agent
from infrastructure.mcp.client.tools import load_qbittorrent_tools
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage


@pytest.mark.expensive
async def test_torrent_agent_with_mcp():
    """Test torrent agent can use MCP tools over HTTP."""

    tools = await load_qbittorrent_tools()
    torrent_agent = create_torrent_agent(tools)

    state = MessagesState(
        messages=[HumanMessage(content="Search for Ubuntu 22.04 torrents")]
    )

    command = torrent_agent.process(state)

    assert command.goto == "supervisor"
    assert len(command.update["messages"]) > 0

    response = command.update["messages"][0].content
    assert "ubuntu" in response.lower() or "search" in response.lower()
