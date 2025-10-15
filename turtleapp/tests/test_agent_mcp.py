"""Test agents using MCP tools (HTTP transport)."""

import pytest
from turtleapp.src.core.nodes.agents import torrent_agent
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage


@pytest.mark.expensive  # Not async - agent.process is synchronous
def test_torrent_agent_with_mcp():
    """Test torrent agent can use MCP tools over HTTP."""

    # Create test state (MessagesState expects dict with messages list)
    state = MessagesState(
        messages=[HumanMessage(content="Search for Ubuntu 22.04 torrents")]
    )

    # Invoke agent (returns Command with goto and update)
    command = torrent_agent.process(state)

    # Check response
    assert command.goto == "supervisor"
    assert len(command.update["messages"]) > 0

    response = command.update["messages"][0].content
    assert "ubuntu" in response.lower() or "search" in response.lower()
